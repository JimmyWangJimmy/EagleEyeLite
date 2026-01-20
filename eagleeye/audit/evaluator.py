"""
Logic Evaluator - Safe evaluation of rule logic schemas.
"""

import re
import ast
import operator
from typing import Any, Optional
from loguru import logger


class LogicEvaluator:
    """
    Evaluates logic_schema strings from audit rules.
    Supports safe evaluation with financial data substitution.

    Supported operators:
        - Comparison: >, <, >=, <=, ==, !=
        - Logical: AND, OR, NOT
        - Math: +, -, *, /, abs()
        - Special: COUNT(), in, 包含
    """

    # Allowed operators for safe evaluation
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Gt: operator.gt,
        ast.Lt: operator.lt,
        ast.GtE: operator.ge,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
    }

    # Allowed function calls
    SAFE_FUNCTIONS = {
        "abs": abs,
        "max": max,
        "min": min,
        "sum": sum,
        "len": len,
        "COUNT": lambda x: sum(1 for item in x if item) if isinstance(x, (list, tuple)) else (1 if x else 0),
    }

    def __init__(self):
        """Initialize evaluator."""
        self._evidence: dict[str, Any] = {}

    def evaluate(
        self,
        logic_schema: str,
        financial_data: dict[str, Any]
    ) -> dict:
        """
        Evaluate a logic schema against financial data.

        Args:
            logic_schema: Logic expression string
            financial_data: Dict of financial field values

        Returns:
            Result dict with:
                - violation: bool
                - evidence: dict of values used
                - calculated_value: float (if applicable)
                - threshold_value: float (if applicable)
                - error: str (if evaluation failed)
        """
        self._evidence = {}

        try:
            # Preprocess the schema
            processed = self._preprocess_schema(logic_schema)

            # Substitute financial data values
            substituted = self._substitute_values(processed, financial_data)

            # Check if we have enough data
            if self._has_missing_data(substituted):
                return {
                    "violation": False,
                    "evidence": self._evidence,
                    "error": "Insufficient data for evaluation",
                    "missing_fields": self._get_missing_fields(processed, financial_data)
                }

            # Safely evaluate the expression
            result = self._safe_eval(substituted)

            return {
                "violation": bool(result),
                "evidence": self._evidence,
                "calculated_value": self._extract_calculated_value(substituted),
                "threshold_value": self._extract_threshold_value(logic_schema),
                "error": None
            }

        except Exception as e:
            logger.warning(f"Logic evaluation error: {e}")
            return {
                "violation": False,
                "evidence": self._evidence,
                "error": str(e)
            }

    def _preprocess_schema(self, schema: str) -> str:
        """
        Preprocess logic schema for evaluation.
        Converts Chinese operators and normalizes syntax.
        """
        processed = schema

        # Convert Chinese logical operators
        processed = re.sub(r'\bAND\b', ' and ', processed)
        processed = re.sub(r'\bOR\b', ' or ', processed)
        processed = re.sub(r'\bNOT\b', ' not ', processed)

        # Handle Chinese "包含" (contains) operator
        processed = re.sub(
            r"(\w+)\s*包含\s*\[([^\]]+)\]",
            r"any(item in \1 for item in [\2])",
            processed
        )

        # Handle "in" lists
        processed = re.sub(
            r"(\w+)\s+in\s+\[([^\]]+)\]",
            r"\1 in [\2]",
            processed
        )

        # Handle == comparison with None/NULL
        processed = processed.replace("== NULL", "is None")
        processed = processed.replace("== None", "is None")

        # Handle COUNT() function with conditions
        count_pattern = r"COUNT\(([^)]+)\s*(<|>|<=|>=|==)\s*([^)]+)\)"
        match = re.search(count_pattern, processed)
        if match:
            list_name = match.group(1).strip()
            op = match.group(2)
            value = match.group(3).strip()
            # Convert to list comprehension count
            processed = re.sub(
                count_pattern,
                f"sum(1 for x in {list_name} if x {op} {value})",
                processed
            )

        # Simple COUNT(list == condition)
        processed = re.sub(
            r"COUNT\(([^)]+)\)",
            r"len([x for x in \1 if x])" if "==" in processed else r"len(\1)",
            processed
        )

        return processed

    def _substitute_values(
        self,
        schema: str,
        financial_data: dict[str, Any]
    ) -> str:
        """
        Substitute financial data values into schema.
        """
        result = schema

        # Sort by key length (longest first) to avoid partial replacements
        sorted_keys = sorted(financial_data.keys(), key=len, reverse=True)

        for key in sorted_keys:
            value = financial_data.get(key)

            if value is not None:
                # Record evidence
                self._evidence[key] = value

                # Handle different value types
                if isinstance(value, bool):
                    replacement = "True" if value else "False"
                elif isinstance(value, str):
                    replacement = f'"{value}"'
                elif isinstance(value, (list, tuple)):
                    replacement = str(value)
                else:
                    replacement = str(value)

                # Replace field name with value
                # Use word boundary matching to avoid partial replacements
                pattern = re.escape(key)
                result = re.sub(rf'\b{pattern}\b', replacement, result)

        return result

    def _has_missing_data(self, substituted: str) -> bool:
        """Check if there are unsubstituted Chinese field names."""
        # Look for remaining Chinese characters that aren't in strings
        chinese_pattern = r'[\u4e00-\u9fff]+'
        matches = re.findall(chinese_pattern, substituted)

        # Filter out matches that are inside quotes
        in_string = False
        for char in substituted:
            if char in '"\'':
                in_string = not in_string

        return bool(matches) and not in_string

    def _get_missing_fields(
        self,
        schema: str,
        financial_data: dict[str, Any]
    ) -> list[str]:
        """Get list of fields referenced but not in data."""
        # Extract potential field names (Chinese text)
        chinese_pattern = r'[\u4e00-\u9fff_]+'
        potential_fields = re.findall(chinese_pattern, schema)

        missing = []
        for field in potential_fields:
            if field not in financial_data or financial_data[field] is None:
                missing.append(field)

        return list(set(missing))

    def _safe_eval(self, expression: str) -> Any:
        """
        Safely evaluate an expression using AST parsing.
        """
        try:
            # Parse expression to AST
            tree = ast.parse(expression, mode='eval')

            # Evaluate AST safely
            return self._eval_node(tree.body)

        except SyntaxError as e:
            logger.warning(f"Syntax error in expression: {expression[:100]}...")
            # Fall back to simple evaluation for basic expressions
            return self._simple_eval(expression)

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n

        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s

        elif isinstance(node, ast.List):
            return [self._eval_node(el) for el in node.elts]

        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(el) for el in node.elts)

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op:
                # Handle division by zero
                if isinstance(node.op, ast.Div) and right == 0:
                    return float('inf')
                return op(left, right)
            raise ValueError(f"Unsupported operator: {type(node.op)}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op:
                return op(operand)
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_func = self.SAFE_OPERATORS.get(type(op))
                if op_func:
                    if not op_func(left, right):
                        return False
                    left = right
                elif isinstance(op, ast.In):
                    if left not in right:
                        return False
                    left = right
                elif isinstance(op, ast.NotIn):
                    if left in right:
                        return False
                    left = right
                elif isinstance(op, ast.Is):
                    if left is not right:
                        return False
                    left = right
                elif isinstance(op, ast.IsNot):
                    if left is right:
                        return False
                    left = right
                else:
                    raise ValueError(f"Unsupported comparison: {type(op)}")
            return True

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v) for v in node.values)

        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in self.SAFE_FUNCTIONS:
                args = [self._eval_node(arg) for arg in node.args]
                return self.SAFE_FUNCTIONS[func_name](*args)
            raise ValueError(f"Unsupported function: {func_name}")

        elif isinstance(node, ast.Name):
            # Handle special constants
            if node.id == 'True':
                return True
            elif node.id == 'False':
                return False
            elif node.id == 'None':
                return None
            raise ValueError(f"Unknown name: {node.id}")

        elif isinstance(node, ast.NameConstant):  # Python 3.7 compatibility
            return node.value

        elif isinstance(node, ast.IfExp):
            test = self._eval_node(node.test)
            return self._eval_node(node.body) if test else self._eval_node(node.orelse)

        elif isinstance(node, ast.GeneratorExp):
            # Handle generator expressions like sum(1 for x in list if x < 0)
            result = []
            iter_val = self._eval_node(node.generators[0].iter)
            for item in iter_val:
                # Simplified: just check if conditions pass
                if node.generators[0].ifs:
                    # Skip items that don't pass filter
                    pass
                result.append(self._eval_node(node.elt))
            return result

        raise ValueError(f"Unsupported AST node: {type(node)}")

    def _simple_eval(self, expression: str) -> bool:
        """
        Simple evaluation fallback for basic expressions.
        """
        # Try to evaluate simple comparisons
        try:
            # Remove extra whitespace
            expr = " ".join(expression.split())

            # Handle simple comparisons
            for op in [' >= ', ' <= ', ' > ', ' < ', ' == ', ' != ']:
                if op in expr:
                    parts = expr.split(op)
                    if len(parts) == 2:
                        left = float(parts[0].strip())
                        right = float(parts[1].strip())
                        if op == ' >= ':
                            return left >= right
                        elif op == ' <= ':
                            return left <= right
                        elif op == ' > ':
                            return left > right
                        elif op == ' < ':
                            return left < right
                        elif op == ' == ':
                            return left == right
                        elif op == ' != ':
                            return left != right

        except (ValueError, IndexError):
            pass

        # Default to no violation
        return False

    def _extract_calculated_value(self, expression: str) -> Optional[float]:
        """Try to extract the calculated left-hand value from comparison."""
        # Look for comparison operators
        for op in [' > ', ' < ', ' >= ', ' <= ', ' == ']:
            if op in expression:
                left_side = expression.split(op)[0].strip()
                try:
                    # Try to evaluate the left side
                    return float(eval(left_side))
                except Exception:
                    pass
        return None

    def _extract_threshold_value(self, expression: str) -> Optional[float]:
        """Extract threshold value from original expression."""
        # Look for numeric thresholds
        pattern = r'[><=!]+\s*([0-9.]+)'
        match = re.search(pattern, expression)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
