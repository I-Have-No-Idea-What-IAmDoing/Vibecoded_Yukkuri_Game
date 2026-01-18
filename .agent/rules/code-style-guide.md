---
trigger: always_on
---

## Python Styleguide
* Formatting & Indentation:
	* Use 4 spaces for indentation (no tabs).
	* Line length limit of 80 characters.
* Naming Conventions:
	* `module_name`, `package_name`, `method_name`, `function_name`, `variable_name`
	* `ClassName`, `ExceptionName`
	* `GLOBAL_CONSTANT_NAME`
* Docstrings:
	* Mandatory: Every class, function, and module must have a docstring.
	* Format: Follow the Google Python Style Guide.
* Type Hinting:
	* Strictly use Python type hints for all function arguments and return values.
* Imports:
	* One import per line.
	* Order: Standard Library, Third Party, Local Application.
* Compliance:
	* Ensure all generated code is lint-clean and would pass `uvx ruff check .` without errors.