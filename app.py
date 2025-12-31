from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
from datetime import datetime, timezone
import re
import pytz
import threading
import os

app = Flask(__name__)

# Conversion counter (thread-safe)
conversion_count = 0
conversion_lock = threading.Lock()
STATS_FILE = 'conversion_stats.txt'

def increment_conversion_count():
    """Increment and save conversion count"""
    global conversion_count
    with conversion_lock:
        conversion_count += 1
        # Save to file for persistence
        try:
            with open(STATS_FILE, 'w') as f:
                f.write(str(conversion_count))
        except Exception:
            pass  # If file write fails, continue with in-memory count

def get_conversion_count():
    """Get current conversion count"""
    global conversion_count
    with conversion_lock:
        # Try to load from file on first access
        if conversion_count == 0:
            try:
                if os.path.exists(STATS_FILE):
                    with open(STATS_FILE, 'r') as f:
                        conversion_count = int(f.read().strip() or '0')
            except Exception:
                pass
        return conversion_count

# Initialize Flask-RESTX API for Swagger documentation
api = Api(app, 
          version='1.0', 
          title='TimePuff Epoch Converter API',
          description='API for converting between epoch time and human-readable datetime',
          prefix='/api',
          doc=False) # Custom /api/docs/ route handles documentation

# Create namespaces
api_v1 = api.namespace('v1', description='JSON API endpoints (v1)')

# Add namespaces to API
api.add_namespace(api_v1)

def normalize_timezone(tz_input):
    """
    Converts timezone abbreviations and friendly names to pytz timezone names.
    Supports abbreviations like 'pst', 'pdt', 'msk' and friendly names like 'pacific', 'moscow'.
    """
    if not tz_input:
        return None
    
    tz_input = tz_input.lower().strip()
    
    # Timezone abbreviation and friendly name mapping
    tz_map = {
        # Pacific timezone
        'pacific': 'America/Los_Angeles',
        'pt': 'America/Los_Angeles',
        'pst': 'America/Los_Angeles',
        'pdt': 'America/Los_Angeles',
        # Eastern timezone
        'eastern': 'America/New_York',
        'et': 'America/New_York',
        'est': 'America/New_York',
        'edt': 'America/New_York',
        # Central timezone
        'central': 'America/Chicago',
        'ct': 'America/Chicago',
        'cst': 'America/Chicago',
        'cdt': 'America/Chicago',
        # Mountain timezone
        'mountain': 'America/Denver',
        'mt': 'America/Denver',
        'mst': 'America/Denver',
        'mdt': 'America/Denver',
        # Moscow timezone
        'moscow': 'Europe/Moscow',
        'msk': 'Europe/Moscow',
        # London timezone
        'london': 'Europe/London',
        'gmt': 'Europe/London',
        # Paris timezone
        'paris': 'Europe/Paris',
        'cet': 'Europe/Paris',
        # Berlin timezone
        'berlin': 'Europe/Berlin',
        # Tokyo timezone
        'tokyo': 'Asia/Tokyo',
        'jst': 'Asia/Tokyo',
        # Shanghai timezone
        'shanghai': 'Asia/Shanghai',
        # Dubai timezone
        'dubai': 'Asia/Dubai',
        'gst': 'Asia/Dubai',
        # Mumbai timezone
        'mumbai': 'Asia/Kolkata',
        'ist': 'Asia/Kolkata',
        # Sydney timezone
        'sydney': 'Australia/Sydney',
        'aest': 'Australia/Sydney',
        # Auckland timezone
        'auckland': 'Pacific/Auckland',
        'nzst': 'Pacific/Auckland',
    }
    
    # Check if it's a mapped abbreviation or friendly name
    if tz_input in tz_map:
        return tz_map[tz_input]
    
    # If not found in map, try to use it as-is (might be a valid pytz timezone name)
    # This allows users to still use full names like 'America/Los_Angeles'
    try:
        pytz.timezone(tz_input)
        return tz_input
    except:
        # If it's not a valid pytz name either, return None (will default to UTC)
        return None

def epoch_to_human(epoch, target_tz=None):
    """Converts epoch seconds (UTC) to formatted datetime string."""
    dt = datetime.fromtimestamp(float(epoch), tz=timezone.utc)
    if target_tz:
        # Normalize timezone abbreviation/friendly name to pytz timezone name
        normalized_tz = normalize_timezone(target_tz)
        if normalized_tz:
            try:
                tz = pytz.timezone(normalized_tz)
                dt = dt.astimezone(tz)
                return dt.strftime('%a %Y-%m-%d %H:%M:%S %Z')
            except Exception:
                pass  # Fall back to UTC if timezone is invalid
    return dt.strftime('%a %Y-%m-%d %H:%M:%S UTC')

def human_to_epoch(human_str, input_tz=None):
    """Converts various datetime formats to epoch seconds."""
    # Helper to localize datetime to timezone then convert to UTC
    def localize_and_convert_to_utc(dt, tz_name):
        if tz_name:
            # Normalize timezone abbreviation/friendly name to pytz timezone name
            normalized_tz = normalize_timezone(tz_name)
            if normalized_tz:
                try:
                    tz = pytz.timezone(normalized_tz)
                    localized_dt = tz.localize(dt, is_dst=None)
                    return int(localized_dt.astimezone(timezone.utc).timestamp())
                except Exception:
                    # Fall back to UTC if timezone is invalid
                    dt = dt.replace(tzinfo=timezone.utc)
                    return int(dt.timestamp())
        # Fall back to UTC if no timezone specified or normalization failed
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    
    # Handle YYYY-MM-DD-HHMMSS format
    if re.match(r'^\d{4}-\d{2}-\d{2}-\d{6}$', human_str):
        dt = datetime.strptime(human_str, '%Y-%m-%d-%H%M%S')
        return localize_and_convert_to_utc(dt, input_tz)
    
    # Handle YYYYMMDDHHMMSS format
    elif re.match(r'^\d{14}$', human_str):
        dt = datetime.strptime(human_str, '%Y%m%d%H%M%S')
        return localize_and_convert_to_utc(dt, input_tz)
    
    # Handle YYYYMMDDHHMM format (no seconds) - default to 00 seconds
    elif re.match(r'^\d{12}$', human_str):
        # Parse as YYYYMMDDHHMM and set seconds to 00
        dt = datetime.strptime(human_str, '%Y%m%d%H%M')
        dt = dt.replace(second=0)
        return localize_and_convert_to_utc(dt, input_tz)
    
    # Handle legacy MM/DD/YYYY HH:MM format
    elif re.match(r'^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}$', human_str):
        dt = datetime.strptime(human_str, '%m/%d/%Y %H:%M')
        return localize_and_convert_to_utc(dt, input_tz)
    
    else:
        raise ValueError("Invalid datetime format. Supported formats: YYYY-MM-DD-HHMMSS, YYYYMMDDHHMMSS, YYYYMMDDHHMM, MM/DD/YYYY HH:MM")

# Define response models for Swagger documentation
epoch_response = api_v1.model('EpochResponse', {
    'epoch': fields.Integer(description='Epoch timestamp', example=1757509860),
    'datetime': fields.String(description='Human readable datetime', example='Wed 2025-09-10 13:11:00'),
    'input': fields.String(description='Original input', example='1757509860')
})

datetime_response = api_v1.model('DateTimeResponse', {
    'epoch': fields.Integer(description='Epoch timestamp', example=1757509860),
    'datetime': fields.String(description='Human readable datetime', example='Wed 2025-09-10 13:11:00'),
    'input': fields.String(description='Original input', example='2025-09-10-131100')
})

error_response = api_v1.model('ErrorResponse', {
    'message': fields.String(description='Error message', example='Invalid datetime format')
})

# JSON API endpoints
@api_v1.route('/epoch/<epoch_time>')
class EpochToDateTime(Resource):
    @api_v1.doc('epoch_to_datetime', description='Convert epoch time to human readable datetime. Supports timezone query parameter (?tz=pst)')
    @api_v1.marshal_with(epoch_response)
    def get(self, epoch_time):
        """Convert epoch time to human readable datetime"""
        try:
            # Convert epoch_time to float to handle both integers and decimals
            epoch_float = float(epoch_time)
            
            # Get timezone parameter from query string
            timezone_param = request.args.get('tz', '').strip()
            human_time = epoch_to_human(epoch_float, target_tz=timezone_param if timezone_param else None)
            return {
                'input': epoch_time,
                'epoch': epoch_float,
                'datetime': human_time
            }
        except ValueError:
            api.abort(400, message="Invalid epoch time format")
        except Exception as e:
            api.abort(400, message=str(e))

@api_v1.route('/datetime/<string:datetime_str>')
class DateTimeToEpoch(Resource):
    @api_v1.doc('datetime_to_epoch', description='Convert human readable datetime to epoch time. Supports timezone query parameter (?tz=pst)')
    @api_v1.marshal_with(datetime_response)
    def get(self, datetime_str):
        """Convert human readable datetime to epoch time"""
        try:
            # Get timezone parameter from query string
            timezone_param = request.args.get('tz', '').strip()
            epoch_time = human_to_epoch(datetime_str, input_tz=timezone_param if timezone_param else None)
            
            # Return in same order as curl: Input, Epoch, DateTime (original input format to match curl)
            return {
                'input': datetime_str,
                'epoch': epoch_time,
                'datetime': datetime_str  # Return original input format to match curl behavior
            }
        except Exception as e:
            api.abort(400, message=str(e))

# Curl-friendly API endpoints (plain text) - direct routes for proper functionality
@app.route('/curl/v1/epoch/<epoch_time>')
def curl_epoch_to_datetime(epoch_time):
    """Convert epoch time to human readable datetime (plain text)"""
    try:
        # Convert epoch_time to float to handle both integers and decimals
        epoch_float = float(epoch_time)
        
        # Get timezone parameter from query string
        timezone_param = request.args.get('tz', '').strip()
        human_time = epoch_to_human(epoch_float, target_tz=timezone_param if timezone_param else None)
        return f"Input:     {epoch_time}\nEpoch:     {epoch_float}\nDatetime:  {human_time}\n\n"
    except ValueError:
        return f"Error: Invalid epoch time format\n\n", 400
    except Exception as e:
        return f"Error: {str(e)}\n\n", 400

@app.route('/curl/v1/datetime/<string:datetime_str>')
def curl_datetime_to_epoch(datetime_str):
    """Convert human readable datetime to epoch time (plain text)"""
    try:
        timezone_param = request.args.get('tz', '').strip()
        epoch_time = human_to_epoch(datetime_str, input_tz=timezone_param if timezone_param else None)
        human_time = epoch_to_human(epoch_time, target_tz=timezone_param if timezone_param else None)
        return f"Input:     {datetime_str}\nEpoch:     {epoch_time}\nDatetime:  {datetime_str}\n\n"
    except Exception as e:
        return f"Error: {str(e)}\n\n", 400

# Custom 404 error handler for curl endpoints
@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors with plain text for curl endpoints, HTML for others"""
    if request.path.startswith('/curl/'):
        return f"Error: Endpoint not found. Check your URL and try again.\n\n", 404
    # For non-curl endpoints, use default HTML 404
    return e

@app.route("/api/v1/swagger.json")
def swagger_json():
    """Generate Swagger JSON for ReDoc"""
    # Flask-RESTX generates spec dynamically, return it as JSON
    # We'll use a simple approach - return the spec URL that Flask-RESTX provides
    # ReDoc needs OpenAPI 3.0, so we'll construct a basic one
    import json
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "TimePuff Epoch Converter API",
            "version": "1.0",
            "description": "API for converting between epoch time and human-readable datetime"
        },
        "servers": [{"url": "/"}],
        "paths": {
            "/api/v1/epoch/{epoch_time}": {
                "get": {
                    "tags": ["JSON API endpoints (v1)"],
                    "summary": "Convert epoch time to human readable datetime",
                    "parameters": [
                        {
                            "name": "epoch_time",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "Epoch timestamp"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "input": {"type": "string", "example": "1757509860"},
                                            "epoch": {"type": "integer", "example": 1757509860},
                                            "datetime": {"type": "string", "example": "Wed 2025-09-10 13:11:00"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/datetime/{datetime_str}": {
                "get": {
                    "tags": ["JSON API endpoints (v1)"],
                    "summary": "Convert human readable datetime to epoch time",
                    "parameters": [
                        {
                            "name": "datetime_str",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Datetime string in various formats"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "input": {"type": "string", "example": "2025-09-10-131100"},
                                            "epoch": {"type": "integer", "example": 1757509860},
                                            "datetime": {"type": "string", "example": "Wed 2025-09-10 13:11:00"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return jsonify(spec)

@app.route("/api/docs/")
def swagger_ui():
    """Custom Swagger UI with snazzy styling"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TimePuff API - Try it out</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
        <link rel="stylesheet" type="text/css" href="/static/swagger-ui.css" />
        <link rel="stylesheet" type="text/css" href="/static/main.css" />
        <style>
            html {{
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }}
            *, *:before, *:after {{
                box-sizing: inherit;
            }}
            body {{
                margin:0;
                background: radial-gradient(ellipse at top, #1a237e 60%, #000 100%);
                font-family: 'Orbitron', 'Consolas', 'Monaco', monospace;
                padding-bottom: 40px;
            }}
            .header-container {{
                background: rgba(22, 26, 70, 0.92);
                border-radius: 20px;
                max-width: 1200px;
                margin: 20px auto;
                padding: 32px;
                text-align: center;
                box-shadow: 0 0 28px #4157dc, 0 0 4px #00eaff;
            }}
            .swagger-header h1 {{
                margin: 0 0 10px 0;
                color: #00eaff;
                letter-spacing: 1px;
                font-size: 3em;
                text-shadow: 0 0 10px #6d28d9, 0 0 20px #7c3aed, 0 0 30px #8b5cf6;
            }}
            .swagger-header h2.subtitle {{
                margin: 0 0 20px 0;
                color: #a78bfa;
                letter-spacing: 0.5px;
                font-size: 1.1em;
                font-weight: normal;
                text-shadow: 0 0 5px rgba(167, 139, 250, 0.5);
                opacity: 0.9;
            }}
            #swagger-ui {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header-container">
            <div class="swagger-header">
                <h1>TimePuff</h1>
                <h2 class="subtitle">The Epic Epoch Date 📅 & Time ⏳ Converter</h2>
            </div>
            <div class="nav-section">
                <a href="/api/docs/" class="nav-button">🚀 Try it out</a>
                <a href="/api/redoc/" class="nav-button">📖 API Docs</a>
                <a href="/stats/" class="nav-button">📊 Stats</a>
                <a href="https://github.com/pbertain/timepuff" target="_blank" class="nav-button">🐙 GitHub</a>
            </div>
        </div>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {{
                // Custom Swagger spec that includes both JSON and CURL endpoints
                const customSpec = {{
                    "swagger": "2.0",
                    "info": {{
                        "title": "TimePuff Epoch Converter API",
                        "version": "1.0",
                        "description": "API for converting between epoch time and human-readable datetime"
                    }},
                    "basePath": "/",
                    "tags": [
                        {{"name": "JSON API endpoints (v1)", "description": "JSON API endpoints (v1)"}},
                        {{"name": "CURL endpoints (v1)", "description": "CURL endpoints (v1)"}}
                    ],
                    "paths": {{
                        "/api/v1/epoch/{{epoch_time}}": {{
                            "get": {{
                                "tags": ["JSON API endpoints (v1)"],
                                "summary": "Convert epoch time to human readable datetime",
                                "description": "Convert epoch time to human readable datetime",
                                "parameters": [
                                    {{
                                        "name": "epoch_time",
                                        "in": "path",
                                        "required": true,
                                        "type": "integer",
                                        "description": "Epoch timestamp"
                                    }}
                                ],
                                "responses": {{
                                    "200": {{
                                        "description": "Success",
                                        "schema": {{
                                            "type": "object",
                                            "properties": {{
                                                "input": {{"type": "string", "example": "1757509860"}},
                                                "epoch": {{"type": "integer", "example": 1757509860}},
                                                "datetime": {{"type": "string", "example": "Wed 2025-09-10 13:11:00"}}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        "/api/v1/datetime/{{datetime_str}}": {{
                            "get": {{
                                "tags": ["JSON API endpoints (v1)"],
                                "summary": "Convert human readable datetime to epoch time",
                                "description": "Convert human readable datetime to epoch time",
                                "parameters": [
                                    {{
                                        "name": "datetime_str",
                                        "in": "path",
                                        "required": true,
                                        "type": "string",
                                        "description": "Datetime string in various formats"
                                    }}
                                ],
                                "responses": {{
                                    "200": {{
                                        "description": "Success",
                                        "schema": {{
                                            "type": "object",
                                            "properties": {{
                                                "input": {{"type": "string", "example": "2025-09-10-131100"}},
                                                "epoch": {{"type": "integer", "example": 1757509860}},
                                                "datetime": {{"type": "string", "example": "Wed 2025-09-10 13:11:00"}}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        "/curl/v1/epoch/{{epoch_time}}": {{
                            "get": {{
                                "tags": ["curl/v1"],
                                "summary": "Convert epoch time to human readable datetime (plain text)",
                                "description": "Convert epoch time to human readable datetime (plain text). Supports decimal epoch times and optional timezone parameter.",
                                "parameters": [
                                    {{
                                        "name": "epoch_time",
                                        "in": "path",
                                        "required": true,
                                        "type": "number",
                                        "description": "Epoch timestamp (supports decimals)"
                                    }},
                                    {{
                                        "name": "tz",
                                        "in": "query",
                                        "required": false,
                                        "type": "string",
                                        "description": "Target timezone (e.g., 'pst', 'utc', 'europe/london')"
                                    }}
                                ],
                                "responses": {{
                                    "200": {{
                                        "description": "Success",
                                        "schema": {{
                                            "type": "string",
                                            "example": "Input:     1757509860\\nEpoch:     1757509860\\nDatetime:  Wed 2025-09-10 13:11:00\\n\\n"
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        "/curl/v1/datetime/{{datetime_str}}": {{
                            "get": {{
                                "tags": ["curl/v1"],
                                "summary": "Convert human readable datetime to epoch time (plain text)",
                                "description": "Convert human readable datetime to epoch time (plain text). Supports optional timezone parameter.",
                                "parameters": [
                                    {{
                                        "name": "datetime_str",
                                        "in": "path",
                                        "required": true,
                                        "type": "string",
                                        "description": "Datetime string in various formats"
                                    }},
                                    {{
                                        "name": "tz",
                                        "in": "query",
                                        "required": false,
                                        "type": "string",
                                        "description": "Input timezone (e.g., 'pst', 'utc', 'europe/london')"
                                    }}
                                ],
                                "responses": {{
                                    "200": {{
                                        "description": "Success",
                                        "schema": {{
                                            "type": "string",
                                            "example": "Input:     2025-09-10-131100\\nEpoch:     1757509860\\nDatetime:  2025-09-10-131100\\n\\n"
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }};
                
                const ui = SwaggerUIBundle({{
                    spec: customSpec,
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout",
                    tryItOutEnabled: true,
                    requestInterceptor: (req) => {{
                        console.log('API Request:', req);
                        return req;
                    }},
                    responseInterceptor: (res) => {{
                        console.log('API Response:', res);
                        return res;
                    }}
                }});
            }};
        </script>
    </body>
    </html>
    """

@app.route("/health")
def health():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}, 200

@app.route("/epoch/<int:epoch_time>")
def restful_epoch(epoch_time):
    """RESTful endpoint to convert epoch to datetime and display result page."""
    timezone_param = request.args.get('tz', '').strip()
    timezone_display = timezone_param if timezone_param else 'UTC'
    
    try:
        # Convert epoch to datetime
        datetime_str = epoch_to_human(epoch_time, target_tz=timezone_param if timezone_param else None)
        increment_conversion_count()
        
        return render_template("result.html",
                             epoch=epoch_time,
                             datetime=datetime_str,
                             input_value=str(epoch_time),
                             timezone=timezone_display if timezone_param else None,
                             error=None)
    except Exception as e:
        return render_template("result.html",
                             epoch=None,
                             datetime=None,
                             input_value=str(epoch_time),
                             timezone=None,
                             error=f"Error: {str(e)}"), 400

@app.route("/datetime/<string:datetime_str>")
def restful_datetime(datetime_str):
    """RESTful endpoint to convert datetime to epoch and display result page."""
    timezone_param = request.args.get('tz', '').strip()
    timezone_display = timezone_param if timezone_param else 'UTC'
    
    try:
        # Handle optional seconds - if 12 digits, append '00' for seconds
        normalized_datetime = datetime_str
        
        # Check if it's a 12-digit YYYYMMDDHHMM format (without seconds)
        if re.match(r'^\d{12}$', datetime_str):
            # Add '00' seconds to make it 14 digits
            normalized_datetime = datetime_str + '00'
        
        # Convert datetime to epoch
        epoch_time = human_to_epoch(normalized_datetime, input_tz=timezone_param if timezone_param else None)
        
        # Get formatted datetime for display
        formatted_datetime = epoch_to_human(epoch_time, target_tz=timezone_param if timezone_param else None)
        increment_conversion_count()
        
        return render_template("result.html",
                             epoch=epoch_time,
                             datetime=formatted_datetime,
                             input_value=datetime_str,
                             timezone=timezone_display,
                             error=None)
    except Exception as e:
        return render_template("result.html",
                             epoch=None,
                             datetime=None,
                             input_value=datetime_str,
                             timezone=None,
                             error=f"Error: {str(e)}"), 400

@app.route("/stats/")
def stats():
    """Display conversion statistics"""
    count = get_conversion_count()
    return render_template("stats.html", conversion_count=count)

@app.route("/api/redoc/")
def redoc():
    """ReDoc API documentation page with matching styling"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TimePuff API Documentation</title>
        <link rel="stylesheet" type="text/css" href="/static/main.css" />
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.css" />
        <style>
            body {{
                margin: 0;
                padding: 20px;
            }}
            .header-container {{
                background: rgba(22, 26, 70, 0.92);
                border-radius: 20px;
                max-width: 1200px;
                margin: 0 auto 20px auto;
                padding: 32px;
                text-align: center;
                box-shadow: 0 0 28px #4157dc, 0 0 4px #00eaff;
            }}
            h1 {{
                margin: 0 0 10px 0;
                color: #00eaff;
                letter-spacing: 1px;
                font-size: 3em;
                text-shadow: 0 0 10px #6d28d9, 0 0 20px #7c3aed, 0 0 30px #8b5cf6;
            }}
            h2.subtitle {{
                margin: 0 0 20px 0;
                color: #a78bfa;
                letter-spacing: 0.5px;
                font-size: 1.1em;
                font-weight: normal;
                text-shadow: 0 0 5px rgba(167, 139, 250, 0.5);
                opacity: 0.9;
            }}
            .nav-section {{
                display: flex;
                justify-content: center;
                gap: 15px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            .nav-button {{
                color: #a78bfa;
                text-decoration: none;
                font-size: 0.9em;
                font-weight: 600;
                padding: 10px 20px;
                border: 2px solid #a78bfa;
                border-radius: 12px;
                background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(167, 139, 250, 0.1));
                transition: all 0.4s ease;
                display: inline-block;
                text-shadow: 0 0 8px rgba(167, 139, 250, 0.6);
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
            }}
            .nav-button:hover {{
                color: #c4b5fd;
                background: linear-gradient(135deg, rgba(139, 92, 246, 0.4), rgba(167, 139, 250, 0.2));
                box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5), 0 0 15px rgba(196, 181, 253, 0.4);
                transform: translateY(-2px) scale(1.05);
                border-color: #c4b5fd;
            }}
            #redoc-container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
        </style>
    </head>
    <body style="background: radial-gradient(ellipse at top, #1a237e 60%, #000 100%); min-height: 100vh; padding-bottom: 40px;">
        <div class="header-container">
            <h1>TimePuff</h1>
            <h2 class="subtitle">The Epic Epoch Date 📅 & Time ⏳ Converter</h2>
            <div class="nav-section">
                <a href="/api/docs/" class="nav-button">🚀 Try it out</a>
                <a href="/api/redoc/" class="nav-button">📖 API Docs</a>
                <a href="/stats/" class="nav-button">📊 Stats</a>
                <a href="https://github.com/pbertain/timepuff" target="_blank" class="nav-button">🐙 GitHub</a>
            </div>
        </div>
        <div id="redoc-container"></div>
        <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
        <script>
            Redoc.init('/api/v1/swagger.json', {{}}, document.getElementById('redoc-container'));
        </script>
    </body>
    </html>
    """

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    direction = None
    input_value = ''
    timezone = ''
    if request.method == "POST":
        direction = request.form.get("direction")
        input_value = request.form.get("input_value")
        timezone = request.form.get("timezone", '')
        try:
            if direction == "epoch_to_human":
                result = epoch_to_human(input_value, target_tz=timezone if timezone else None)
            else:
                result = human_to_epoch(input_value, input_tz=timezone if timezone else None)
            if result and not str(result).startswith("Error"):
                increment_conversion_count()
        except Exception as e:
            result = f"Error: {e}"
    return render_template("index.html", result=result, direction=direction, input_value=input_value, timezone=timezone)

if __name__ == "__main__":
    import os
    # Use environment variable for port, default to 33080 for production
    port = int(os.environ.get('PORT', 33080))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="127.0.0.1", port=port, debug=debug)