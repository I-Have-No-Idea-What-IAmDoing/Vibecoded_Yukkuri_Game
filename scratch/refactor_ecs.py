
with open('src/yukkuri_game/engine/ecs.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add decorator definition
decorator_code = '''
from collections.abc import Callable
from functools import wraps

def ensure_context(func: Callable) -> Callable:
    """Decorator to ensure operations run within this world's context."""
    @wraps(func)
    def wrapper(self: "World", *args: Any, **kwargs: Any) -> Any:
        self._switch()
        return func(self, *args, **kwargs)
    return wrapper
'''
code = code.replace('from collections.abc import Iterator\n', 'from collections.abc import Iterator, Callable\nfrom functools import wraps\n')
code = code.replace('class World:\n', decorator_code + '\nclass World:\n')

methods = [
    'create_entity', 'destroy_entity', 'entity_exists', 'add_component',
    'remove_component', 'get_component', 'try_get_component', 'has_component',
    'get_components', 'get_entities_with', 'get_components_tuple',
    'get_all_components', 'add_system', 'update', 'clear_database', 'destroy'
]

# Simple matching: replace 'self._switch()' with '' inside the methods
# and add @ensure_context before the 'def ...'
for method in methods:
    # Match:
    #     def create_entity(self, *components: Any) -> int:
    #         """..."""
    #         self._switch()
    # It might span multiple lines.
    
    # Let's find the def line and the first self._switch() inside it.
    def_idx = code.find(f"    def {method}(self")
    if def_idx != -1:
        # Find next self._switch()
        switch_idx = code.find("        self._switch()\n", def_idx)
        if switch_idx != -1 and switch_idx < def_idx + 1000: # Ensure it's in the same method
            # Remove the switch
            code = code[:switch_idx] + code[switch_idx + len("        self._switch()\n"):]
            # Add @ensure_context above def
            code = code[:def_idx] + "    @ensure_context\n" + code[def_idx:]

with open('src/yukkuri_game/engine/ecs.py', 'w', encoding='utf-8') as f:
    f.write(code)
