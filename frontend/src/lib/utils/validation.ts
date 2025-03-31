/**
 * Validates if a string is a valid Python identifier
 * @param str String to validate
 * @returns boolean indicating if the string is a valid Python identifier
 */
export function isValidPythonIdentifier(str: string): boolean {
    // Python identifiers must start with a letter or underscore
    // and can only contain letters, numbers, and underscores
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(str);
}

/**
 * Validates if a string is a valid Python class name
 * @param str String to validate
 * @returns boolean indicating if the string is a valid Python class name
 */
export function isValidPythonClassName(str: string): boolean {
    // Python class names should follow PEP8 and be in CamelCase
    // They should start with an uppercase letter and only contain letters and numbers
    return /^[A-Z][a-zA-Z0-9]*$/.test(str);
}

/**
 * Python reserved keywords that can't be used as identifiers
 */
export const PYTHON_RESERVED_KEYWORDS = [
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
    'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
    'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
    'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
]; 