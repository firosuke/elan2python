# elan2python

Python program to translate a file in the Elan programming language into Python. Created in an afternoon with (a lot of) AI prompting and a little hand-crafting.

You can learn about and use the Elan language here:

https://elan-lang.org/

If you have Python 3 installed, download and run the script e.g. as follows:

```
python3 elan2python.py <input-path> [<output-path>]
```

If there are no arguments or more than three, this help message is displayed:

```
Elan-to-Python Translator
=========================

Usage: python elan2python.py <input_file.elan> [output_file.py]

Arguments:
  input_file.elan   : Path to the input Elan source file (mandatory)
  output_file.py    : Path to the output Python file (optional, defaults to 'output.py')
                      Note: If already exists, will only overwrite default 'output.py'
Examples:
  python elan2python.py program.elan
  python elan2python.py program.elan converted.py
  python elan2python.py examples/octagon.elan graphics/octagon.py
```

If no input path is provided (i.e. no arguments are present), by default it will translate some Elan code and show you the results as a demonstration.

Remember, whatever you code -- do it with *é l a n*\~
