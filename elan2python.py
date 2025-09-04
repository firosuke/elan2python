import re
import sys
from typing import List, Dict, Optional

class ElanToPythonTranslator:
    def __init__(self):
        self.output_lines = []
        self.indent_level = 0
        self.imports_needed = set()
        self.in_main = False
        self.variables = {}
        self.out_params = []  # Track out parameters for current function
        self.procedure_out_positions = {}
        
    def translate(self, elan_code: str) -> str:
        """Main translatation method"""
        lines = elan_code.strip().split('\n')
        
        # First pass: analyze code structure
        self.analyze_code(lines)
        
        # Add necessary imports at the beginning
        self.add_imports()
        
        # Second pass: translate each line
        for line in lines:
            self.translate_line(line.rstrip())
            
        return '\n'.join(self.output_lines)
    
    def analyze_code(self, lines: List[str]):
        """Analyze code to determine what imports are needed"""
        for line in lines:
            line = line.strip()
            #if any(keyword in line for keyword in ['turtle.', 'clearScreen', 'penDown', 'penUp', 'forward', 'turn']):
            if "Turtle" in line:
                self.imports_needed.add('turtle')
            # Track procedure definitions with out parameters
            self.analyze_procedure_signature(line)
    
    def analyze_procedure_signature(self, line: str):
        """Analyze procedure/function definitions to track out parameter positions"""
        # Match procedure or function definitions with parameters
        proc_match = re.match(r'(procedure|function)\s+(\w+)\s*\(([^)]*)\)', line)
        if not proc_match:
            return
            
        func_type, func_name, params_str = proc_match.groups()
        
        if not params_str.strip():
            return
            
        # Parse parameters to find out parameter positions
        param_list = [p.strip() for p in params_str.split(',')]
        out_positions = []
        
        for i, param in enumerate(param_list):
            if param.startswith("out "):
                out_positions.append(i)
        
        # Store the out parameter positions for this procedure
        if out_positions:
            self.procedure_out_positions[func_name] = out_positions

    def add_imports(self):
        """Add necessary Python imports"""
        if 'turtle' in self.imports_needed:
            self.output_lines.extend([
                "import turtle",
                "import math",
                "",
                "# Initialize turtle graphics",
                "screen = turtle.Screen()",
                "t = turtle.Turtle()",
                "t.speed(6)",
                "",
                "def clearScreen():",
                "    screen.clear()",
                "    global t",
                "    t = turtle.Turtle()",
                "    t.speed(6)",
                ""
            ])
    
    def translate_line(self, line: str):
        """Translate a single line of Elan code"""
        original_line = line
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            if line.startswith('#'):
                self.add_line(line)
            elif original_line.strip() == "":
                self.add_line("")
            return
        
        # Handle main program
        if line == "main":
            self.add_line("def main():")
            self.indent_level += 1
            self.in_main = True
            return
            
        if line == "end main":
            self.indent_level -= 1
            self.add_line("")
            self.add_line("if __name__ == '__main__':")
            self.add_line("    main()", force_indent=1)
            if 'turtle' in self.imports_needed:
                self.add_line("    screen.exitonclick()", force_indent=1)
            return
        
        # Handle procedures and functions
        if line.startswith("procedure ") or line.startswith("function "):
            self.translate_procedure_function(line)
            return
            
        if line.startswith("end procedure") or line.startswith("end function"):
            # Add return statement for out parameters if any exist
            if hasattr(self, 'out_params') and self.out_params:
                if len(self.out_params) == 1:
                    self.add_line(f"return {self.out_params[0]}")
                else:
                    self.add_line(f"return {', '.join(self.out_params)}")
                self.out_params = []  # Clear out parameters
            self.indent_level -= 1
            self.add_line("")
            return
        
        # Handle control structures
        if line.startswith("if "):
            self.translate_if(line)
            return
            
        if line.startswith("else"):
            self.translate_else(line)
            return
            
        if line.startswith("end if"):
            self.indent_level -= 1
            return
        
        if line.startswith("repeat ") and "times" in line:
            self.translate_repeat(line)
            return
            
        if line == "end repeat":
            self.indent_level -= 1
            return
            
        if line.startswith("while "):
            self.translate_while(line)
            return
            
        if line.startswith("end while"):
            self.indent_level -= 1
            return
        
        if line.startswith("for "):
            self.translate_for(line)
            return
            
        if line.startswith("end for"):
            self.indent_level -= 1
            return
        
        if line.startswith("each "):
            self.translate_each(line)
            return
            
        if line == "end each":
            self.indent_level -= 1
            return
        
        # Handle variable declarations and assignments - MUST come before call handling
        if self.is_assignment_or_declaration(line):
            self.translate_assignment(line)
            return
        
        # Handle procedure/function calls
        if line.startswith("call "):
            self.translate_call(line)
            return
        
        # Handle return statements
        if line.startswith("return"):
            self.translate_return(line)
            return
        
        # Handle print/output statements
        if line.startswith("print ") or line.startswith("println "):
            self.translate_print(line)
            return
        
        # Default: try to handle as expression or statement
        self.add_line(line)
    
    def is_assignment_or_declaration(self, line: str) -> bool:
        """Check if line is an assignment or declaration"""
        line = line.strip()
        # More specific patterns to avoid false positives
        return (
            line.startswith("variable ") and " set to " in line or
            line.startswith("set ") and " to " in line or
            ((" = " in line) and not line.startswith("call ") and not "==" in line and not "!=" in line)
        )
    
    def translate_assignment(self, line: str):
        """Handle variable assignments and declarations"""
        line = line.strip()
        
        # Handle "variable x set to value" pattern
        if line.startswith("variable ") and " set to " in line:
            match = re.match(r'variable\s+(\w+)\s+set to\s+(.+)', line)
            if match:
                var_name, value = match.groups()
                value = self.convert_expression(value)
                self.add_line(f"{var_name} = {value}")
                return
            

        
        # Handle "set x to value" pattern
        if line.startswith("set ") and " to " in line:
            match = re.match(r'set\s+(.+?)\s+to\s+(.+)', line)
            if match:
                var_name, value = match.groups()
                var_name = var_name.strip()
                value = self.convert_expression(value.strip())
                self.add_line(f"{var_name} = {value}")
                return
        
        # Handle regular assignment "x = value"
        if " = " in line and not "==" in line and not "!=" in line:
            parts = line.split(" = ", 1)
            if len(parts) == 2:
                var_name = parts[0].strip()
                value = parts[1].strip()
                value = self.convert_expression(value)
                self.add_line(f"{var_name} = {value}")
                return
        
        # If we get here, something went wrong
        self.add_line(f"# ASSIGNMENT ERROR: {line}")
    
    def translate_procedure_function(self, line: str):
        """Handle procedure and function definitions"""
        # Extract name and parameters
        match = re.match(r'(procedure|function)\s+(\w+)\s*\((.*?)\)', line)
        if match:
            func_type, name, params = match.groups()
            python_params, out_params = self.convert_parameters(params)
            self.add_line(f"def {name}({python_params}):")
            self.indent_level += 1
            # Store out parameters for this function
            if out_params:
                self.out_params = out_params
            else:
                self.out_params = []
        else:
            # Handle parameterless procedure/function
            match = re.match(r'(procedure|function)\s+(\w+)', line)
            if match:
                func_type, name = match.groups()
                self.add_line(f"def {name}():")
                self.indent_level += 1
                self.out_params = []
    
    def convert_parameters(self, params: str) -> tuple:
        """Convert Elan parameters to Python parameters with type annotations and extract out parameters"""
        if not params.strip():
            return "", []
        
        param_list = [p.strip() for p in params.split(',')]
        python_params = []
        out_params = []
        
        for param in param_list:
            # Handle out parameters
            if param.startswith("out "):
                param_name = param[4:].strip()  # Remove "out " prefix
                # Handle typed out parameters (e.g., "out x as Int")
                if " as " in param_name:
                    name, elan_type = param_name.split(" as ", 1)
                    name = name.strip()
                    elan_type = elan_type.strip()
                    python_type = self.convert_elan_type_to_python(elan_type)
                    python_params.append(f"{name}: {python_type}")
                    out_params.append(name)  # Fixed: use the extracted name
                else:
                    python_params.append(param_name)
                    out_params.append(param_name)
            elif " as " in param:
                # Handle typed parameters (e.g., "x as Int")
                name, elan_type = param.split(" as ", 1)
                name = name.strip()
                elan_type = elan_type.strip()
                python_type = self.convert_elan_type_to_python(elan_type)
                python_params.append(f"{name}: {python_type}")
            else:
                python_params.append(param)
        
        return ", ".join(python_params), out_params
    
    def convert_elan_type_to_python(self, elan_type: str) -> str:
        """Convert Elan type annotations to Python type annotations"""
        if not elan_type or elan_type.strip() == "":
            return ""
            
        elan_type = elan_type.strip()
        
        # Handle basic types
        type_mapping = {
            'Int': 'int',
            'Float': 'float', 
            'Bool': 'bool',
            'Boolean': 'bool',
            'String': 'str',
            'Str': 'str'
        }
        
        if elan_type in type_mapping:
            return type_mapping[elan_type]
            
        # Handle Array types: Array<of Int> -> List[int]
        if elan_type.startswith('Array<of ') and elan_type.endswith('>'):
            inner_type = elan_type[9:-1]  # Extract type between 'Array<of ' and '>'
            python_inner = self.convert_elan_type_to_python(inner_type)
            return f"List[{python_inner}]"
            
        # Handle List types: List<of Int> -> List[int] 
        if elan_type.startswith('List<of ') and elan_type.endswith('>'):
            inner_type = elan_type[8:-1]  # Extract type between 'List<of ' and '>'
            python_inner = self.convert_elan_type_to_python(inner_type)
            return f"List[{python_inner}]"
            
        # Handle Dictionary types: Dictionary<of String, Int> -> Dict[str, int]
        if elan_type.startswith('Dictionary<of ') and elan_type.endswith('>'):
            inner_types = elan_type[14:-1]  # Extract types between 'Dictionary<of ' and '>'
            if ',' in inner_types:
                key_type, value_type = [t.strip() for t in inner_types.split(',', 1)]
                python_key = self.convert_elan_type_to_python(key_type)
                python_value = self.convert_elan_type_to_python(value_type)
                return f"Dict[{python_key}, {python_value}]"
                
        # Handle Optional types or return as-is for unknown types
        return elan_type
    
    def translate_each(self, line: str):
        """Handle each loops (for-each style)"""
        # Handle: each x in collection
        match = re.match(r'each\s+(\w+)\s+in\s+(.+)', line)
        if match:
            var, collection = match.groups()
            collection = self.convert_expression(collection)
            self.add_line(f"for {var} in {collection}:")
            self.indent_level += 1
    
    def translate_for(self, line: str):
        """Handle for loops"""
        # Handle different for loop patterns
        if " from " in line and " to " in line:
            # Handle: for i from start to end [step n]
            if " step " in line:
                match = re.match(r'for\s+(\w+)\s+from\s+(.+?)\s+to\s+(.+?)\s+step\s+(.+)', line)
                if match:
                    var, start, end, step = match.groups()
                    start = self.convert_expression(start.strip())
                    end = self.convert_expression(end.strip())
                    step = self.convert_expression(step.strip())
                    self.add_line(f"for {var} in range({start}, {end} + 1, {step}):")
                    self.indent_level += 1
                    return
            else:
                # for i from start to end (no step)
                match = re.match(r'for\s+(\w+)\s+from\s+(.+?)\s+to\s+(.+)', line)
                if match:
                    var, start, end = match.groups()
                    start = self.convert_expression(start.strip())
                    end = self.convert_expression(end.strip())
                    self.add_line(f"for {var} in range({start}, {end} + 1):")
                    self.indent_level += 1
                    return
        elif " in " in line:
            # for item in collection
            match = re.match(r'for\s+(\w+)\s+in\s+(.+)', line)
            if match:
                var, collection = match.groups()
                collection = self.convert_expression(collection)
                self.add_line(f"for {var} in {collection}:")
                self.indent_level += 1
                return
        
        # If no pattern matched, output error
        self.add_line(f"# FOR LOOP ERROR: {line}")
    
    def translate_if(self, line: str):
        """Handle if statements"""
        condition = line[3:].strip()  # Remove 'if '
        if condition.endswith(" then"):
            condition = condition[:-5]  # Remove ' then'
        condition = self.convert_condition(condition)
        self.add_line(f"if {condition}:")
        self.indent_level += 1
    
    def translate_else(self, line: str):
        """Handle else statements"""
        self.indent_level -= 1
        if line.strip() == "else":
            self.add_line("else:")
        else:
            # Handle 'else if' -> 'elif'
            condition = line[7:].strip()  # Remove 'else if '
            if condition.endswith(" then"):
                condition = condition[:-5]
            condition = self.convert_condition(condition)
            self.add_line(f"elif {condition}:")
        self.indent_level += 1
    
    def translate_repeat(self, line: str):
        """Handle repeat...times loops"""
        match = re.match(r'repeat\s+(.+?)\s+times', line)
        if match:
            count = match.group(1)
            self.add_line(f"for _ in range({count}):")
            self.indent_level += 1
    
    def translate_while(self, line: str):
        """Handle while loops"""
        condition = line[6:].strip()  # Remove 'while '
        condition = self.convert_condition(condition)
        self.add_line(f"while {condition}:")
        self.indent_level += 1
    
    def translate_call(self, line: str):
        """Handle procedure/function calls"""
        call_part = line[5:].strip()  # Remove 'call '
        
        # Handle array assignment with put method: a.put(i, v) -> a[i] = v
        if ".put(" in call_part and call_part.endswith(")"):
            match = re.match(r'(\w+)\.put\(([^,]+),\s*(.+)\)', call_part)
            if match:
                array_name, index, value = match.groups()
                index = self.convert_expression(index.strip())
                value = self.convert_expression(value.strip())
                self.add_line(f"{array_name}[{index}] = {value}")
                return
        
        # Handle turtle graphics calls
        turtle_mapping = {
            'clearScreen()': 'clearScreen()',
            'turtle.penDown()': 't.pendown()',
            'turtle.penUp()': 't.penup()',
            'turtle.forward(': 't.forward(',
            'turtle.turnRight(': 't.right(',
            'turtle.turnLeft(': 't.left(',
        }
        
        for elan_call, python_call in turtle_mapping.items():
            if call_part.startswith(elan_call.split('(')[0]):
                if '(' in elan_call:
                    # Handle parameterized calls
                    param_start = call_part.find('(')
                    if param_start != -1:
                        params = call_part[param_start:]
                        self.add_line(f"{python_call.split('(')[0]}{params}")
                        return
                else:
                    self.add_line(python_call)
                    return
        
        # Handle procedure calls with out parameters
        # Extract function name and arguments
        func_call_match = re.match(r'(\w+)\s*\(([^)]*)\)', call_part)
        if func_call_match:
            func_name, args_str = func_call_match.groups()
            
            # Check if this procedure has out parameters
            if func_name in self.procedure_out_positions:
                out_positions = self.procedure_out_positions[func_name]
                
                if out_positions and args_str.strip():
                    # Parse the arguments
                    args = [arg.strip() for arg in args_str.split(',')]
                    
                    # Get the arguments at out parameter positions
                    out_args = []
                    for pos in out_positions:
                        if pos < len(args):
                            out_args.append(args[pos])
                    
                    if out_args:
                        # Generate assignment based on number of out parameters
                        if len(out_args) == 1:
                            self.add_line(f"{out_args[0]} = {call_part}")
                        else:
                            out_args_str = ", ".join(out_args)
                            self.add_line(f"{out_args_str} = {call_part}")
                        return
        
        # Default call handling - just remove "call" and output the function call
        self.add_line(call_part)
    
    def translate_return(self, line: str):
        """Handle return statements"""
        if line.strip() == "return":
            self.add_line("return")
        else:
            value = line[6:].strip()  # Remove 'return'
            value = self.convert_expression(value)
            self.add_line(f"return {value}")
    
    def translate_print(self, line: str):
        """Handle print statements"""
        if line.startswith("print "):
            content = line[6:].strip()
            content = self.convert_expression(content)
            self.add_line(f"print({content}, end='')")
        elif line.startswith("println "):
            content = line[8:].strip()
            content = self.convert_expression(content)
            self.add_line(f"print({content})")
    
    def convert_condition(self, condition: str) -> str:
        """Convert Elan conditions to Python conditions"""
        # Handle comparison operators
        condition = condition.replace(" is ", " == ")
        condition = condition.replace(" = ", " == ")
        condition = condition.replace(" <> ", " != ")
        
        # Handle logical operators
        condition = condition.replace(" and ", " and ")
        condition = condition.replace(" or ", " or ")
        condition = condition.replace(" not ", " not ")
        
        # Handle arithmetic operators
        condition = self.convert_expression(condition)
        
        return condition
    
    def convert_expression(self, expr: str) -> str:
        """Convert Elan expressions to Python expressions"""
        if not expr:
            return expr
            
        # Handle string concatenation
        expr = expr.replace(" & ", " + ")
        
        # Handle Array literals: [1, 2, 3].asArray() -> [1, 2, 3]
        expr = re.sub(r'(\[[^\]]*\])\.asArray\(\)', r'\1', expr)
        
        # Handle Array creation: new Array<of Int>(n, v) -> n * [v]  
        expr = re.sub(r'new Array<[^>]*>\(([^,]+),\s*([^)]+)\)', r'(\1) * [\2]', expr)
        
        # Handle empty Array: empty Array<of Int> -> []
        expr = re.sub(r'empty Array<[^>]*>', r'[]', expr)
        
        # Handle slice syntax with comprehensive patterns
        # Pattern: identifier[start..end] -> identifier[start:end]
        expr = re.sub(r'(\w+(?:\[[^\]]*\])*)\[([^.\]]*)\.\.\]', r'\1[\2:]', expr)  # a[1..] -> a[1:]
        expr = re.sub(r'(\w+(?:\[[^\]]*\])*)\[\.\.([^.\]]*)\]', r'\1[:\2]', expr)  # a[..5] -> a[:5]
        expr = re.sub(r'(\w+(?:\[[^\]]*\])*)\[([^.\]]*)\.\.([^.\]]*)\]', r'\1[\2:\3]', expr)  # a[1..5] -> a[1:5]
        
        # Handle div operator with word boundaries to avoid partial matches
        # This regex ensures we only replace "div" when it's a separate word
        expr = re.sub(r'\b(\w+(?:\([^)]*\))?(?:\[[^\]]*\])?(?:\.\w+(?:\([^)]*\))?)*)\s+div\s+(\w+(?:\([^)]*\))?(?:\[[^\]]*\])?(?:\.\w+(?:\([^)]*\))?)*)', r'\1 // \2', expr)
        expr = re.sub(r'\b(\w+)\s+div\s+(\d+)', r'\1 // \2', expr)  # simple cases
        expr = re.sub(r'\b(\d+)\s+div\s+(\w+)', r'\1 // \2', expr)
        expr = re.sub(r'\b(\d+)\s+div\s+(\d+)', r'\1 // \2', expr)
        
        # Handle mod operator
        expr = expr.replace(" mod ", " % ")
        
        # Handle boolean literals
        expr = expr.replace("true", "True")
        expr = expr.replace("false", "False")
        
        return expr
    
    def add_line(self, line: str, force_indent: Optional[int] = None):
        """Add a line with proper indentation"""
        indent = force_indent if force_indent is not None else self.indent_level
        indented_line = "    " * indent + line if line.strip() else ""
        self.output_lines.append(indented_line)

def translate_elan_to_python(elan_code: str) -> str:
    """Main function to translate Elan code to Python"""
    translator = ElanToPythonTranslator()
    return translator.translate(elan_code)

def print_help():
    """Print help message for command-line usage"""
    print("Elan-to-Python Translator")
    print("=" * 25)
    print()
    print("Usage: python elan2python.py <input_file.elan> [output_file.py]")
    print()
    print("Arguments:")
    print("  input_file.elan   : Path to the input Elan source file (mandatory)")
    print("  output_file.py    : Path to the output Python file (optional, defaults to 'output.py')")
    print("                      Note: If already exists, will only overwrite default 'output.py'")
    print()
    print("Examples:")
    print("  python elan2python.py program.elan")
    print("  python elan2python.py program.elan converted.py")
    print("  python elan2python.py examples/octagon.elan graphics/octagon.py")

def main_cli():
    """Main function for command-line interface"""
    import argparse
    import os
    
    # Handle no arguments case
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Error: Input file is required.")
        print()
        print_help()
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.py"
    
    # Check if too many arguments
    if len(sys.argv) > 3:
        print("Error: Too many arguments provided.")
        print()
        print_help()
        sys.exit(1)
    
    # Validate input file
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)
    
    if not os.path.isfile(input_file):
        print(f"Error: '{input_file}' is not a regular file.")
        sys.exit(1)
    
    # Check if input file has .elan extension (warning, not error)
    if not input_file.lower().endswith('.elan'):
        print(f"Warning: Input file '{input_file}' does not have a .elan extension.")
    
    # Check if output file already exists
    if output_file != "output.py" and os.path.exists(output_file):
        print(f"Error: Non-default output file '{output_file}' already exists.")
        print("Please choose a different output file name or remove the existing file.")
        sys.exit(1)
    
    # Check if output directory exists and is writable
    output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "."
    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist.")
        sys.exit(1)
    
    if not os.access(output_dir, os.W_OK):
        print(f"Error: Cannot write to output directory '{output_dir}'. Permission denied.")
        sys.exit(1)
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            elan_code = f.read()
    except IOError as e:
        print(f"Error reading input file '{input_file}': {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Input file '{input_file}' contains invalid UTF-8 characters: {e}")
        sys.exit(1)
    
    # Translate the code
    try:
        python_code = translate_elan_to_python(elan_code)
    except Exception as e:
        print(f"Error during translatation: {e}")
        sys.exit(1)
    
    # Write output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(python_code)
        print(f"Successfully translated '{input_file}' to '{output_file}'")
        print(f"Output file size: {len(python_code)} characters")
    except IOError as e:
        print(f"Error writing output file '{output_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error writing output file '{output_file}': {e}")
        sys.exit(1)

# Main entry point with test
if __name__ == "__main__":
    # First, test with a simple example to verify the fixes work
    if len(sys.argv) == 1:
        print("Testing the translator with key patterns:")
        print("=" * 50)
        
        test_elan_code = """procedure f(out x as Int, out y as Int)
  set x to 5
  set y to 6
end procedure

procedure add_lists(a as Array<of Int>, b as Array<of Int>, out result as Array<of Int>)
  set result to new Array<of Int>(a.length(), 0)
  for i from 0 to a.length() - 1 step 1
    set result[i] to a[i] + b[i]
  end for
end procedure

main
  variable u set to 0
  variable v set to 0
  call f(u, v)
  
  variable arr1 set to [1, 2, 3].asArray()
  variable arr2 set to [4, 5, 6].asArray()
  variable result set to empty Array<of Int>
  call add_lists(arr1, arr2, result)
  
  print "u = " & u.asString()
  print "v = " & v.asString()
end main"""

        python_code = translate_elan_to_python(test_elan_code)
        print(python_code)
        print("=" * 50)
        print("\nIf all works correctly, you should see:")
        print("- Type annotations: def f(x: int, y: int) -> tuple[int, int]:")
        print("- Procedure calls with assignment: u, v = f(u, v)")
        print("- result = add_lists(arr1, arr2, result)")
        print("- Proper array/slice conversions")
        print("=" * 50)
    
    main_cli()