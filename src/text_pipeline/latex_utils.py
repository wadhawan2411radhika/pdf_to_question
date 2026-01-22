"""
latex_utils.py

Utility functions for robust LaTeX and Unicode math handling in PDF extraction.
- Detects LaTeX/math content in text
- Converts Unicode math symbols and letters to LaTeX
- Expands coverage to Greek, sub/superscripts, and more
"""
import re

# Unicode math alphanumerics (comprehensive mapping)
UNICODE_MATH_LETTERS = {
    # Mathematical italic small letters (U+1D44E to U+1D467)
    '\U0001D44E': 'a', '\U0001D44F': 'b', '\U0001D450': 'c', '\U0001D451': 'd',
    '\U0001D452': 'e', '\U0001D453': 'f', '\U0001D454': 'g', '\U0001D455': 'h',
    '\U0001D456': 'i', '\U0001D457': 'j', '\U0001D458': 'k', '\U0001D459': 'l', 
    '\U0001D45A': 'm', '\U0001D45B': 'n', '\U0001D45C': 'o', '\U0001D45D': 'p', 
    '\U0001D45E': 'q', '\U0001D45F': 'r', '\U0001D460': 's', '\U0001D461': 't', 
    '\U0001D462': 'u', '\U0001D463': 'v', '\U0001D464': 'w', '\U0001D465': 'x', 
    '\U0001D466': 'y', '\U0001D467': 'z',
    
    # Mathematical italic capital letters (U+1D434 to U+1D44D)
    '\U0001D434': 'A', '\U0001D435': 'B', '\U0001D436': 'C', '\U0001D437': 'D',
    '\U0001D438': 'E', '\U0001D439': 'F', '\U0001D43A': 'G', '\U0001D43B': 'H',
    '\U0001D43C': 'I', '\U0001D43D': 'J', '\U0001D43E': 'K', '\U0001D43F': 'L',
    '\U0001D440': 'M', '\U0001D441': 'N', '\U0001D442': 'O', '\U0001D443': 'P',
    '\U0001D444': 'Q', '\U0001D445': 'R', '\U0001D446': 'S', '\U0001D447': 'T',
    '\U0001D448': 'U', '\U0001D449': 'V', '\U0001D44A': 'W', '\U0001D44B': 'X',
    '\U0001D44C': 'Y', '\U0001D44D': 'Z',
    
    # Mathematical bold italic small letters (U+1D482 to U+1D49B)
    '\U0001D482': 'a', '\U0001D483': 'b', '\U0001D484': 'c', '\U0001D485': 'd',
    '\U0001D486': 'e', '\U0001D487': 'f', '\U0001D488': 'g', '\U0001D489': 'h',
    '\U0001D48A': 'i', '\U0001D48B': 'j', '\U0001D48C': 'k', '\U0001D48D': 'l',
    '\U0001D48E': 'm', '\U0001D48F': 'n', '\U0001D490': 'o', '\U0001D491': 'p',
    '\U0001D492': 'q', '\U0001D493': 'r', '\U0001D494': 's', '\U0001D495': 't',
    '\U0001D496': 'u', '\U0001D497': 'v', '\U0001D498': 'w', '\U0001D499': 'x',
    '\U0001D49A': 'y', '\U0001D49B': 'z',
    
    # Mathematical bold italic capital letters (U+1D468 to U+1D481)
    '\U0001D468': 'A', '\U0001D469': 'B', '\U0001D46A': 'C', '\U0001D46B': 'D',
    '\U0001D46C': 'E', '\U0001D46D': 'F', '\U0001D46E': 'G', '\U0001D46F': 'H',
    '\U0001D470': 'I', '\U0001D471': 'J', '\U0001D472': 'K', '\U0001D473': 'L',
    '\U0001D474': 'M', '\U0001D475': 'N', '\U0001D476': 'O', '\U0001D477': 'P',
    '\U0001D478': 'Q', '\U0001D479': 'R', '\U0001D47A': 'S', '\U0001D47B': 'T',
    '\U0001D47C': 'U', '\U0001D47D': 'V', '\U0001D47E': 'W', '\U0001D47F': 'X',
    '\U0001D480': 'Y', '\U0001D481': 'Z',
    
    # Mathematical monospace digits (U+1D7CE to U+1D7D7)
    '\U0001D7CE': '0', '\U0001D7CF': '1', '\U0001D7D0': '2', '\U0001D7D1': '3',
    '\U0001D7D2': '4', '\U0001D7D3': '5', '\U0001D7D4': '6', '\U0001D7D5': '7',
    '\U0001D7D6': '8', '\U0001D7D7': '9',
    
    # Mathematical double-struck digits (U+1D7D8 to U+1D7E1)
    '\U0001D7D8': '0', '\U0001D7D9': '1', '\U0001D7DA': '2', '\U0001D7DB': '3',
    '\U0001D7DC': '4', '\U0001D7DD': '5', '\U0001D7DE': '6', '\U0001D7DF': '7',
    '\U0001D7E0': '8', '\U0001D7E1': '9',
    
    # Mathematical sans-serif digits (U+1D7E2 to U+1D7EB)
    '\U0001D7E2': '0', '\U0001D7E3': '1', '\U0001D7E4': '2', '\U0001D7E5': '3',
    '\U0001D7E6': '4', '\U0001D7E7': '5', '\U0001D7E8': '6', '\U0001D7E9': '7',
    '\U0001D7EA': '8', '\U0001D7EB': '9',
    
    # Mathematical sans-serif bold digits (U+1D7EC to U+1D7F5)
    '\U0001D7EC': '0', '\U0001D7ED': '1', '\U0001D7EE': '2', '\U0001D7EF': '3',
    '\U0001D7F0': '4', '\U0001D7F1': '5', '\U0001D7F2': '6', '\U0001D7F3': '7',
    '\U0001D7F4': '8', '\U0001D7F5': '9',
}

# Common math symbols and their LaTeX equivalents
UNICODE_TO_LATEX = {
    '∑': r'\sum',
    '∞': r'\infty',
    '→': r'\to',
    '±': r'\pm',
    '×': r'\times',
    '÷': r'\div',
    '≠': r'\neq',
    '≤': r'\leq',
    '≥': r'\geq',
    '√': r'\sqrt{}',
    '∫': r'\int',
    '∂': r'\partial',
    '∈': r'\in',
    '∩': r'\cap',
    '∪': r'\cup',
    '∅': r'\emptyset',
    '∃': r'\exists',
    '∀': r'\forall',
    '∇': r'\nabla',
    '≈': r'\approx',
    '≅': r'\cong',
    '≡': r'\equiv',
    '∝': r'\propto',
    '∠': r'\angle',
    '∴': r'\therefore',
    '∵': r'\because',
    # Additional symbols found in the PDF
    '−': r'-',  # Unicode minus sign (U+2212)
    '…': r'\ldots',  # Horizontal ellipsis (U+2026)
    '‒': r'-',  # Figure dash (U+2012)
    '–': r'-',  # En dash (U+2013)
    '—': r'-',  # Em dash (U+2014)
    ' ': r' ',  # Various Unicode spaces
    '\u2004': r'\quad',  # Three-per-em space
    '\u2009': r'\,',  # Thin space
    '\u00A0': r'~',  # Non-breaking space
    # Fractions
    '½': r'\frac{1}{2}',
    '⅓': r'\frac{1}{3}',
    '⅔': r'\frac{2}{3}',
    '¼': r'\frac{1}{4}',
    '¾': r'\frac{3}{4}',
    '⅛': r'\frac{1}{8}',
    # Additional mathematical operators
    '∏': r'\prod',
    '∐': r'\coprod',
    '∘': r'\circ',
    '∙': r'\cdot',
    '∗': r'\ast',
    '⋅': r'\cdot',
    '⋆': r'\star',
    '∆': r'\Delta',
    '∇': r'\nabla',
}

# Greek letters (partial)
GREEK_TO_LATEX = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta', 'ε': r'\epsilon',
    'θ': r'\theta', 'λ': r'\lambda', 'μ': r'\mu', 'π': r'\pi', 'ρ': r'\rho',
    'σ': r'\sigma', 'τ': r'\tau', 'φ': r'\phi', 'ω': r'\omega',
    'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda', 'Π': r'\Pi',
    'Σ': r'\Sigma', 'Φ': r'\Phi', 'Ω': r'\Omega',
}

# Subscript and superscript mappings (only valid pairs)
SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'h': 'ₕ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ',
    's': 'ₛ', 't': 'ₜ', 'i': 'ᵢ', 'r': 'ᵣ', 'u': 'ᵤ', 'v': 'ᵥ', 
    'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ'
}
SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ',
    'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ',
    'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ',
    't': 'ᵗ', 'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ'
}

# Regex for LaTeX/math detection (expand as needed)
LATEX_REGEXES = [
    r'\\[a-zA-Z]+',  # LaTeX commands
    r'\$.*?\$',      # Inline math
    r'\[\(\[].*?[\)\]]',  # Display math
    r'[∑∞→±×÷≠≤≥√∫∂∈∩∪∅∃∀∇≈≅≡∝∠∴∵−…‒–—∏∐∘∙∗⋅⋆∆]',  # Common math symbols
    r'[α-ωΑ-Ω]',      # Greek letters
    r'[₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹ₐₑₒₓₕₖₗₘₙₚₛₜᵢᵣᵤᵥᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⁺⁻⁼⁽⁾]',  # Sub/superscripts
    r'[\U0001D434-\U0001D467]',  # Mathematical italic capital letters
    r'[\U0001D44E-\U0001D467]',  # Mathematical italic small letters  
    r'[\U0001D468-\U0001D481]',  # Mathematical bold italic capital letters
    r'[\U0001D482-\U0001D49B]',  # Mathematical bold italic small letters
    r'[\u2004\u2009\u00A0]',     # Special Unicode spaces
    # Add more as needed
]

LATEX_REGEX = re.compile('|'.join(LATEX_REGEXES))

def detect_latex(text: str) -> bool:
    """Detect if text contains LaTeX or math symbols."""
    if not text:
        return False
    
    # Check for Unicode mathematical letters and digits
    for char in text:
        if ('\U0001D434' <= char <= '\U0001D49B' or  # Mathematical alphanumeric symbols
            '\U0001D7CE' <= char <= '\U0001D7F5'):   # Mathematical digits
            return True
    
    # Check other patterns
    return bool(LATEX_REGEX.search(text))

def render_latex(text: str) -> str:
    """Convert Unicode math symbols, Greek, and math letters to LaTeX."""
    # Replace Unicode math letters
    for uni, ascii_char in UNICODE_MATH_LETTERS.items():
        text = text.replace(uni, ascii_char)
    # Replace Greek letters
    for uni, latex in GREEK_TO_LATEX.items():
        text = text.replace(uni, latex)
    # Replace math symbols
    for uni, latex in UNICODE_TO_LATEX.items():
        text = text.replace(uni, latex)
    # Optionally, handle sub/superscripts (basic)
    def subscript_to_latex(match):
        base = match.group(1)
        subs = match.group(2)
        latex_sub = ''.join(str(list(SUBSCRIPT_MAP.keys())[list(SUBSCRIPT_MAP.values()).index(c)]) if c in SUBSCRIPT_MAP.values() else c for c in subs)
        return f"{{{base}}}_{{{latex_sub}}}"

    def superscript_to_latex(match):
        base = match.group(1)
        sups = match.group(2)
        latex_sup = ''.join(str(list(SUPERSCRIPT_MAP.keys())[list(SUPERSCRIPT_MAP.values()).index(c)]) if c in SUPERSCRIPT_MAP.values() else c for c in sups)
        return f"{{{base}}}^{{{latex_sup}}}"

    text = re.sub(r'([A-Za-z])([₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₕₖₗₘₙₚₛₜᵤᵥ]+)', subscript_to_latex, text)
    text = re.sub(r'([A-Za-z])([⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⁺⁻⁼⁽⁾]+)', superscript_to_latex, text)
    return text
