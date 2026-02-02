import re
import random
from typing import Dict, Any

def process_template_variations(template: str) -> str:
    """
    Process template with {option1|option2|option3} syntax.
    Randomly selects one option from each variation group.

    Example: "Hello {bro|dude|friend}" -> "Hello dude"

    Args:
        template: Template string with {option1|option2|...} patterns

    Returns:
        Processed string with random variations selected
    """
    def replace_variation(match):
        options = match.group(1).split('|')
        return random.choice(options)

    # Find all {option1|option2|...} patterns and replace with random choice
    result = re.sub(r'\{([^}]+\|[^}]+)\}', replace_variation, template)
    return result


def process_template_with_variables(template: str, variables: Dict[str, Any] = None) -> str:
    """
    Process template with both variations and variable substitution.
    First applies variations, then substitutes variables.

    Example:
        template = "Hello {bro|dude} {name}, check {this|it} out!"
        variables = {"name": "Alice"}
        result = "Hello dude Alice, check this out!"

    Args:
        template: Template string with {variations} and {variables}
        variables: Dict of variable name -> value mappings

    Returns:
        Fully processed string
    """
    # First process variations
    result = process_template_variations(template)

    # Then substitute variables if provided
    if variables:
        for key, value in variables.items():
            result = result.replace(f'{{{key}}}', str(value))

    return result
