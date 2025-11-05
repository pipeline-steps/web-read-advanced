"""Template resolution with JSONPath expression support."""

import sys
import re
from typing import List
from jsonpath_ng import parse


class TemplateResolver:
    """Resolves template strings containing JSONPath expressions."""

    @staticmethod
    def resolve(template: str, json_data: dict) -> List[str]:
        """
        Resolve a template string with JSONPath expressions.

        Template strings can contain ${...} expressions where the content
        is a JSONPath expression. These are evaluated against the json_data
        and replaced with the matched values.

        Args:
            template: Template string containing ${jsonpath} expressions
            json_data: JSON data to evaluate JSONPath expressions against

        Returns:
            List of resolved strings. Returns empty list if any expression
            fails to match or if there's a parsing error.

        Example:
            >>> template = '{"id": ${items[*].id}, "name": "${items[*].name}"}'
            >>> data = {"items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
            >>> TemplateResolver.resolve(template, data)
            ['{"id": 1, "name": "A"}', '{"id": 2, "name": "B"}']
        """
        if not template:
            return []

        results = [template]

        # Find all ${...} expressions
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, template)

        for jsonpath_expr in matches:
            try:
                jsonpath = parse(jsonpath_expr)
                matches_obj = jsonpath.find(json_data)

                if not matches_obj:
                    # No match found, return empty
                    return []

                # Get all matched values
                values = [match.value for match in matches_obj]

                # Expand results for each value
                new_results = []
                for result in results:
                    for value in values:
                        new_results.append(result.replace(f'${{{jsonpath_expr}}}', str(value)))
                results = new_results

            except Exception as e:
                print(f"Error parsing JSONPath '{jsonpath_expr}': {e}", file=sys.stderr)
                return []

        return results
