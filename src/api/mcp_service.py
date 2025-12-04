"""Define and implement all tools for the MCP server here."""

from datetime import datetime, timezone as UTC
from typing import Dict, Any, Callable, Optional, List, Union
import typing

from pydantic import BaseModel, Field, ValidationError, create_model
from pydantic_core import PydanticUndefined
from .models import ToolCallResult
from fastmcp import FastMCP, Context
import json
import os
import inspect
from .cosmos_service import log_mcp_tool_call, get_cosmos_service
from datetime import datetime, timezone



#----------------------------------- HELPER FUNCTIONS -----------------------------------#

def extract_correlation_headers(context: Context):
    """Extract and log correlation headers from MCP request context."""
    # Handle case where context is None (e.g., MCP inspector)
    if context is None or not hasattr(context, 'request_context') or context.request_context is None:
        print("No context available (likely MCP inspector), using default headers")
        return {}, "unknown", "unknown"
    
    headers = context.request_context.request.headers
    print(f"Headers received in MCP tool: {headers}")
    
    # Extract correlation headers for logging
    correlation_id_header = headers.get("x-correlationid", "unknown")
    test_case_id_header = headers.get("x-testcaseid", "unknown")
    print(f"Correlation headers - Correlation ID: {correlation_id_header}, Test Case ID: {test_case_id_header}")
    
    return headers, correlation_id_header, test_case_id_header

async def log_tool_call_with_headers(headers, correlation_id, testcase_id, tool_name, params, result):
    """Log MCP tool call using correlation headers for more reliable tracking."""
    header_correlation_id = headers.get("x-correlationid", correlation_id)
    header_test_case_id = headers.get("x-testcaseid", testcase_id)
    
    await log_mcp_tool_call(header_correlation_id, header_test_case_id, tool_name, params, result)


#----------------------------------- TOOL LOADING -----------------------------------#

# Global storage for tool mock types mapping: {tool_name: [supported_mock_types]}
_TOOL_MOCK_TYPES_CACHE: Dict[str, List[str]] = {}

    
def _safe_json_parse(json_str: str) -> Dict[str, Any]:
        """Safely parse JSON string with potential escape sequence issues"""
        try:
            # First try normal JSON parsing
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Initial JSON parse failed: {e}")
            # If that fails, try to fix common escape sequence issues
            try:
                # Step 1: Fix invalid escape sequences like \' and \" that aren't properly escaped
                fixed_str = json_str
                
                # Fix \' (invalid escape) to proper unicode escape
                fixed_str = fixed_str.replace("\\'", "\\u0027")
                # Fix \" (invalid escape) to proper unicode escape
                fixed_str = fixed_str.replace('\\"', "\\u0022")
                
                # Fix standalone backslashes in regex patterns
                # This handles patterns like ^[^\s@]+@[^\s@]+\.[^\s@]{2,}$ 
                # Replace \s, \d, etc. with proper escaping for JSON
                import re
                # Find all regex-like patterns and properly escape them
                fixed_str = re.sub(r'\\([sd@+.])', r'\\\\\\1', fixed_str)
                
                return json.loads(fixed_str)
                
            except json.JSONDecodeError as e:
                try:
                    # Step 2: Try a more comprehensive fix
                    print(f"Second attempt failed: {e}")
                    
                    # More aggressive cleaning - handle multiple problematic patterns
                    fixed_str = json_str
                    
                    # Replace problematic escape sequences
                    replacements = [
                        ("\\'", "'"),  # Remove invalid \' 
                        ('\\"', '"'),  # Remove invalid \" 
                        ("\\\\", "\\"),  # Fix double backslashes
                        ("\\u002B", "+"),  # Replace unicode plus
                        ("\\u0027", "'"),  # Replace unicode apostrophe
                        ("\\u0022", '"'),  # Replace unicode quotation mark
                    ]
                    
                    for old, new in replacements:
                        fixed_str = fixed_str.replace(old, new)
                    
                    # Clean up regex patterns by escaping backslashes properly
                    # Find patterns like "pattern":"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$"
                    pattern_regex = r'"pattern":"([^"]*\\[^"]*)"'
                    def escape_pattern(match):
                        # Properly escape backslashes in the matched pattern
                        pattern = match.group(1)
                        escaped_pattern = pattern.replace('\\', r'\\\\')
                        return f'"pattern":"{escaped_pattern}"'
                    
                    fixed_str = re.sub(pattern_regex, escape_pattern, fixed_str)
                    
                    return json.loads(fixed_str)
                    
                except json.JSONDecodeError as e:
                    try:
                        # Step 3: Last resort - try to parse with lenient approach
                        print(f"Third attempt failed: {e}")
                        
                        # Try to use ast.literal_eval approach with careful string replacement
                        import ast
                        fixed_str = json_str
                        
                        # Replace with valid JSON escape sequences
                        fixed_str = fixed_str.replace("\\'", "'")
                        fixed_str = fixed_str.replace('\\"', '"')
                        # Try to fix other common issues
                        fixed_str = re.sub(r'\\([^"\\\/bfnrtu])', r'\\\\\\1', fixed_str)
                        
                        return json.loads(fixed_str)
                        
                    except (json.JSONDecodeError, ValueError, SyntaxError) as final_e:
                        # If all else fails, return a basic schema and log the error
                        print(f"All JSON parsing attempts failed: {final_e}")
                        print(f"Problematic JSON (first 700 chars): {json_str[:700]}")
                        return {"servers": []}

def _load_tool_definitions(definitions_file:str = "tool-definitions.json") -> Dict[str, Any]:
        """Load tool definitions from JSON file"""
        try:
            # Support both absolute and relative paths
            if os.path.isabs(definitions_file):
                definitions_path = definitions_file
            else:
                definitions_path = os.path.join(os.path.dirname(__file__), definitions_file)
            
            with open(definitions_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Use the safe JSON parser to handle potential escape issues
                return _safe_json_parse(content)
        except Exception as e:
            print(f"Warning: Could not load {definitions_file}: {e}")
            return {"servers": []}

def _parse_tool_schemas(tool_definitions) -> Dict[str, BaseModel]:
        """Parse JSON schemas from tool definitions and create Pydantic models"""
        tool_schemas = {}
        
        for server in tool_definitions.get("servers", []):
            for tool_def in server.get("tools", []):
                tool_name = tool_def.get("name")
                json_schema_data = tool_def.get("json_input_schema")
                
                if not tool_name or not json_schema_data:
                    continue
                
                try:
                    # The json_input_schema is already parsed when loading the JSON file
                    # If it's a string, we need to parse it; if it's already a dict, use it directly
                    if isinstance(json_schema_data, str):
                        # Handle potential escape sequence issues by attempting multiple parsing strategies
                        json_schema = _safe_json_parse(json_schema_data)
                    else:
                        json_schema = json_schema_data

                    # # Create Pydantic model from schema
                    # pydantic_model = _create_pydantic_model_from_schema(tool_name, json_schema)
                    # tool_schemas[tool_name] = pydantic_model
                    tool_schemas[tool_name] = json_schema
                    
                    print(f"Created schema for tool: {tool_name}")
                    
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Warning: Could not parse schema for tool {tool_name}: {e}")
                
        return tool_schemas
   
   
def _convert_json_schema_to_pydantic_field(field_schema: Dict[str, Any], is_required: bool = False):
        """Convert a JSON schema field to Pydantic field type and info"""
        field_type = field_schema.get("type", "string")
        description = field_schema.get("description", "")


        
        # Map JSON schema types to Python types
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "List[Any]",
            "object": "object"
        }
        
        python_type = type_mapping.get(field_type, "str")
        
        # Handle arrays with specific item types
        if field_type == "array":
            items_schema = field_schema.get("items", {})
            if items_schema:
                item_type = items_schema.get("type", "string")
                item_python_type = type_mapping.get(item_type, "str")
                python_type = f'List[{item_python_type}]'
                return python_type
        
        # Handle optional fields
        if not is_required:
            python_type = f'Optional[{python_type}]'
        
        return python_type

def _wrap_default_function(tool_name: str, description: str, tool_schemas) -> Callable:
    """Create a wrapper function for dynamic tool registration"""
    schema_json = tool_schemas.get(tool_name)
    doc_lines = [description, ""]
    optional_param_defs = []
    optional_param_names = []
    required_param_defs = []
    required_param_names = []
    if schema_json:
        properties = schema_json.get("properties", {})
        required_fields = schema_json.get("required", [])

        def flatten_object(parent_name, obj_schema, parent_required):
            obj_props = obj_schema.get("properties", {})
            obj_required = obj_schema.get("required", [])
            for sub_name, sub_schema in obj_props.items():
                full_name = f"{parent_name}_{sub_name}"
                is_sub_required = sub_name in obj_required and parent_required
                sub_type = _convert_json_schema_to_pydantic_field(sub_schema, is_sub_required)
                sub_default = sub_schema.get("default", None)
                if 'List' in sub_type and sub_default is None:
                    sub_default = "[]"
                if 'object' in sub_type:
                    flatten_object(full_name, sub_schema, is_sub_required)
                else:
                    if is_sub_required:
                        required_param_names.append(full_name)
                        required_param_defs.append(f"{full_name}: {sub_type}")
                        doc_lines.append(f":param {full_name}: {sub_schema.get('description', '')} (required)")
                    else:
                        optional_param_names.append(full_name)
                        optional_param_defs.append(f"{full_name}: {sub_type} = {sub_default}")
                        doc_lines.append(f":param {full_name}: {sub_schema.get('description', '')} (optional)")

        for param_name, param_schema in properties.items():
            is_required = param_name in required_fields
            param_type = _convert_json_schema_to_pydantic_field(param_schema, is_required)
            param_default = param_schema.get("default", None)
            if 'List' in param_type and param_default is None:
                param_default = "[]"
            if param_name == 'from':
                param_name = 'sender'
            if "object" in param_type:
                flatten_object(param_name, param_schema, is_required)
            else:
                if is_required:
                    required_param_names.append(param_name)
                    required_param_defs.append(f"{param_name}: {param_type}")
                    doc_lines.append(f":param {param_name}: {param_schema.get('description', '')} (required)")
                else:
                    optional_param_names.append(param_name)
                    optional_param_defs.append(f"{param_name}: {param_type} = {param_default}")
                    doc_lines.append(f":param {param_name}: {param_schema.get('description', '')} (optional)")
    else:
        required_param_defs.append('args')
        required_param_names.append('args')
        doc_lines.append(":param args: JSON string of parameters")

    params_str = ", ".join(filter(None, (required_param_defs or []) + (optional_param_defs or [])))
    all_param_names = required_param_names + optional_param_names
    docstring = "\n".join(doc_lines)

    # Build function code string


    func_code = f"def tool_wrapper(context: Context, {params_str}):\n"
    func_code += f"    '''{docstring}'''\n"
    func_code +=f"    try:\n"
    if schema_json:
        func_code += f"        param_dict = {{k: v for k, v in locals().items() if k in {all_param_names!r}}}\n"
        # No validation, just pass param_dict
    else:
        func_code += f"        import json\n"
        func_code += f"        param_dict = json.loads(args) if args else {{}}\n"
    func_code += f"        return generic_tool_call('{tool_name}', param_dict, context)\n"
    func_code +=f"    except Exception as e:\n"
    func_code += f"        return ToolCallResult(success=False, error=f'{{str(e)}}')\n"

    import typing
    local_ns = {
        "schema_json": schema_json
    }
    global_ns = {
        "Optional": typing.Optional,
        "List": typing.List,
        "Union": typing.Union,
        "Any": typing.Any,
        "Dict": typing.Dict,
        "Optional[List[str]]": typing.Optional[typing.List[str]],
        "ToolCallResult": ToolCallResult,
        "None": type(None),
        "generic_tool_call": generic_tool_call,
        "Context": Context
    }
    exec(func_code, global_ns, local_ns)
    tool_wrapper = local_ns["tool_wrapper"]
    tool_wrapper.__doc__ = docstring
    return tool_wrapper

def register_tools(mcp: FastMCP, tool_definitions, tool_schemas):
        """Register all tools from tool-definitions.json with the MCP server"""
        registered_count = 0
        
        for server in tool_definitions.get("servers", []):
            server_name = server.get("name", "unknown")
            
            for tool_def in server.get("tools", []):
                tool_name = tool_def.get("name")
                description = tool_def.get("description", f"Tool: {tool_name}")
                supported_mock_types = tool_def.get("supportedMockTypes", [])
                
                if not tool_name:
                    print(f"Warning: Tool without name found in server {server_name}")
                    continue
                
                # Cache the tool's supported mock types
                _TOOL_MOCK_TYPES_CACHE[tool_name] = supported_mock_types
                
                # Create and register the tool wrapper
                wrapper = _wrap_default_function(tool_name, description, tool_schemas)
                
                try:
                    # Register the tool with FastMCP
                    mcp.tool(wrapper, name=tool_name)
                    registered_count += 1
                    print(f"Registered tool: {tool_name}")
                except Exception as e:
                    print(f"Error registering tool {tool_name}: {e}")
        
        print(f"Successfully registered {registered_count} tools")

def load_and_register_tools(mcp: FastMCP, definitions_file: str = "tool-definitions.json"):
    """Convenience function to load and register all tools"""
    tool_definitions = _load_tool_definitions()
    tool_schemas = _parse_tool_schemas(tool_definitions)
    register_tools(mcp, tool_definitions, tool_schemas)


#----------------------------------- CALENDAR TOOLS -----------------------------------#

async def generic_tool_call(tool_name: str, params: Dict[str, Any], context: Context = None) -> ToolCallResult:
    """Generic tool call handler that can access supportedMockTypes for each tool"""

    headers, correlation_id, testcase_id = extract_correlation_headers(context)
    supported_mock_types = _TOOL_MOCK_TYPES_CACHE.get(tool_name, [])
    
    print(f"Calling tool: {tool_name}")
    print(f"Supported mock types: {supported_mock_types}")
    print(f"Parameters: {params}")
    
    # Handle specific tools
    if tool_name in ["sendMail", "mcp_CalendarTools_graph_createEvent"]:
        # For create operations, return sanitized params directly
        result = ToolCallResult(
            success=True,
            tool_result_data=params  # Params are already sanitized by wrapper functions
        )
    else:
        # For other tools, fetch test case and return mock data based on supported mock types
        try:
            cosmos_service = get_cosmos_service()
            
            test_case = None
            if testcase_id and testcase_id != "unknown":
                test_case = await cosmos_service.get_testcase_by_id(testcase_id)
            
            if not supported_mock_types:
                result = ToolCallResult(
                    success=True,
                    tool_result_data={}
                )
            elif test_case and hasattr(test_case, 'references_seed'):
                references_seed = test_case.references_seed
                for seed_key, seed_value in references_seed.items():
                    # seed_value is a Pydantic model (EmailMock, TeamsMock, etc.) with a 'kind' attribute
                    seed_kind = getattr(seed_value, 'kind', '')
                    if seed_kind in supported_mock_types:
                        result = ToolCallResult(
                            success=True,
                            tool_result_data=seed_value.model_dump()
                        )
                        break
                else:
                    result = ToolCallResult(
                        success=True,
                        tool_result_data={
                            "message": f"No matching mock type found for {tool_name}",
                            "availableMockTypes": list(getattr(seed_value, 'kind', '') for seed_value in references_seed.values())
                        }
                    )
            else:
                result = ToolCallResult(
                    success=True,
                    tool_result_data={
                        "message": f"No test case or references_seed found for {tool_name}"
                    }
                )
        except Exception as e:
            print(f"Error in mock data retrieval: {e}")
            result = ToolCallResult(
                success=True,
                tool_result_data={
                    "message": f"Error retrieving mock data for {tool_name}",
                    "error": str(e)
                }
            )
    
    # Log the tool call
    await log_tool_call_with_headers(headers, correlation_id, testcase_id, tool_name, params, result)
    return result
