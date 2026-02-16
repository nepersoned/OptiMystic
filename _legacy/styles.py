# styles.py
# Modern Design System - OptiMystic Pro (Polished)

# === COLOR PALETTE ===
PRIMARY_COLOR = '#60a5fa'
SECONDARY_COLOR = '#1e40af'
SUCCESS_COLOR = '#10b981'
WARNING_COLOR = '#f59e0b'
ERROR_COLOR = '#ef4444'
DARK_BG = '#0f172a'
LIGHT_BG = '#f6fbff'
NEUTRAL_50 = '#f8fafc'
NEUTRAL_100 = '#f3f4f6'
NEUTRAL_200 = '#e6eefc'
NEUTRAL_300 = '#d1d5db'
NEUTRAL_400 = '#9ca3af'
NEUTRAL_700 = '#374151'
NEUTRAL_900 = '#0b1220'

# === TYPOGRAPHY ===
FONT_FAMILY = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial"
HEADER_FONT_WEIGHT = '800'

# === SPACING ===
SPACING_XS = '8px'
SPACING_SM = '10px'
SPACING_MD = '14px'
SPACING_LG = '20px'
SPACING_XL = '24px'
SPACING_2XL = '32px'

# === BORDERS & SHADOWS ===
BORDER_RADIUS_SM = '6px'
BORDER_RADIUS_MD = '10px'
BORDER_RADIUS_LG = '14px'
BORDER_RADIUS_XL = '18px'

SHADOW_SM = '0 1px 2px rgba(12, 18, 28, 0.04)'
SHADOW_MD = '0 8px 20px rgba(12, 18, 28, 0.08)'
SHADOW_LG = '0 20px 40px rgba(12, 18, 28, 0.10)'
SHADOW_XL = '0 30px 60px rgba(12, 18, 28, 0.12)'

# === TABLE STYLING ===
TABLE_CONTAINER_STYLE = {
    'borderRadius': BORDER_RADIUS_LG,
    'overflow': 'hidden',
    'border': f'1px solid {NEUTRAL_200}',
    'marginBottom': SPACING_LG,
    'fontFamily': FONT_FAMILY,
    'boxShadow': SHADOW_SM,
    'backgroundColor': 'white'
}

TABLE_HEADER_STYLE = {
    'backgroundColor': NEUTRAL_100,
    'color': NEUTRAL_700,
    'fontWeight': '700',
    'textAlign': 'center',
    'padding': f'{SPACING_SM} {SPACING_MD}',
    'border': f'1px solid {NEUTRAL_200}',
    'fontSize': '12px',
    'textTransform': 'uppercase',
    'letterSpacing': '0.5px',
    'fontFamily': FONT_FAMILY
}

TABLE_CELL_STYLE = {
    'padding': f'{SPACING_SM} {SPACING_MD}',
    'border': f'1px solid {NEUTRAL_100}',
    'fontSize': '13px',
    'textAlign': 'left',
    'color': NEUTRAL_900,
    'fontFamily': FONT_FAMILY
}

# === CARD STYLING ===
CARD_STYLE = {
    'padding': SPACING_XL,
    'borderRadius': BORDER_RADIUS_XL,
    'backgroundColor': 'white',
    'border': f'1px solid {NEUTRAL_200}',
    'boxShadow': SHADOW_SM,
    'fontFamily': FONT_FAMILY
}

# === INSIGHT BOX ===
INSIGHT_BOX_STYLE = {
    'backgroundColor': LIGHT_BG,
    'padding': SPACING_LG,
    'borderRadius': BORDER_RADIUS_LG,
    'borderLeft': f'5px solid {PRIMARY_COLOR}',
    'marginBottom': SPACING_2XL,
    'color': NEUTRAL_700,
    'lineHeight': '1.7',
    'fontFamily': FONT_FAMILY,
    'boxShadow': SHADOW_SM
}

# === BUTTONS ===
PRIMARY_BTN_STYLE = {
    'width': '100%',
    'padding': f'{SPACING_SM} {SPACING_LG}',
    'backgroundColor': PRIMARY_COLOR,
    'color': 'white',
    'fontSize': '15px',
    'border': 'none',
    'borderRadius': BORDER_RADIUS_LG,
    'cursor': 'pointer',
    'fontWeight': '700',
    'boxShadow': SHADOW_MD,
    'fontFamily': FONT_FAMILY,
    'letterSpacing': '0.4px'
}

ADD_BTN_STYLE = {
    'width': '100%',
    'padding': SPACING_SM,
    'border': f'2px dashed {PRIMARY_COLOR}',
    'borderRadius': BORDER_RADIUS_LG,
    'backgroundColor': 'transparent',
    'color': PRIMARY_COLOR,
    'fontWeight': '700',
    'fontSize': '14px',
    'cursor': 'pointer',
    'marginTop': SPACING_MD,
    'fontFamily': FONT_FAMILY
}

SMALL_BTN_STYLE = {
    'padding': f'{SPACING_SM} {SPACING_MD}',
    'backgroundColor': 'transparent',
    'color': PRIMARY_COLOR,
    'fontSize': '13px',
    'border': f'1px solid {NEUTRAL_200}',
    'borderRadius': BORDER_RADIUS_MD,
    'cursor': 'pointer',
    'fontWeight': '600',
    'fontFamily': FONT_FAMILY
}

# === STATUS MESSAGE ===
STATUS_MSG_STYLE = {
    'textAlign': 'center',
    'fontWeight': '700',
    'color': PRIMARY_COLOR,
    'fontSize': '14px',
    'padding': SPACING_LG,
    'borderRadius': BORDER_RADIUS_LG,
    'backgroundColor': LIGHT_BG,
    'border': f'1px solid {PRIMARY_COLOR}',
    'fontFamily': FONT_FAMILY
}

# === INPUT & LABEL ===
INPUT_LABEL_STYLE = {
    'fontWeight': '700',
    'fontSize': '14px',
    'color': NEUTRAL_900,
    'display': 'block',
    'marginBottom': SPACING_SM,
    'fontFamily': FONT_FAMILY
}

INPUT_FIELD_STYLE = {
    'width': '100%',
    'padding': f'{SPACING_SM} {SPACING_MD}',
    'fontSize': '14px',
    'border': f'1px solid {NEUTRAL_300}',
    'borderRadius': BORDER_RADIUS_MD,
    'fontFamily': FONT_FAMILY,
    'backgroundColor': 'white',
    'color': NEUTRAL_900,
    'transition': 'border-color 0.18s ease, box-shadow 0.18s ease'
}

# === HEADER ===
HEADER_STYLE = {
    'backgroundColor': DARK_BG,
    'padding': SPACING_XL,
    'boxShadow': SHADOW_MD,
    'borderBottom': f'3px solid {PRIMARY_COLOR}'
}

HEADER_TITLE_STYLE = {
    'color': 'white',
    'margin': 0,
    'fontWeight': HEADER_FONT_WEIGHT,
    'fontSize': '24px',
    'fontFamily': FONT_FAMILY,
    'letterSpacing': '-0.5px'
}

# === SECTIONS ===
SECTION_CONTAINER_STYLE = {
    'padding': SPACING_2XL,
    'backgroundColor': NEUTRAL_50
}

SECTION_HEADER_STYLE = {
    'marginBottom': SPACING_2XL,
    'borderLeft': f'5px solid {PRIMARY_COLOR}',
    'paddingLeft': SPACING_LG
}

SECTION_TITLE_STYLE = {
    'color': NEUTRAL_900,
    'fontWeight': HEADER_FONT_WEIGHT,
    'margin': 0,
    'fontSize': '20px',
    'fontFamily': FONT_FAMILY
}

SECTION_SUBTITLE_STYLE = {
    'color': NEUTRAL_700,
    'fontSize': '13px',
    'marginTop': SPACING_SM,
    'fontFamily': FONT_FAMILY
}

# === MAIN CONTAINER ===
MAIN_CONTAINER_STYLE = {
    'width': '100%',
    'maxWidth': '1200px',
    'margin': '24px auto',
    'padding': SPACING_LG,
    'backgroundColor': 'white',
    'borderRadius': BORDER_RADIUS_XL,
    'overflow': 'hidden',
    'boxShadow': SHADOW_XL,
    'fontFamily': FONT_FAMILY
}

# === GLOBAL CSS ===
# These are injected into the Dash app via external_stylesheets or assets.
FIXED_CSS = [
    {'selector': '*', 'rule': f"font-family: {FONT_FAMILY} !important; box-sizing: border-box;"},
    {'selector': 'body', 'rule': f"background-color: {NEUTRAL_50} !important; color: {NEUTRAL_900} !important;"},
    {'selector': 'input:focus, select:focus, textarea:focus', 'rule': f"border-color: {PRIMARY_COLOR} !important; outline: none; box-shadow: 0 6px 18px rgba(96,165,250,0.06);"},
    {'selector': '.dash-table-container', 'rule': 'border-radius: 12px; overflow: hidden;'},
    {'selector': '.dash-table-container .dash-spreadsheet-container td', 'rule': 'padding: 8px 12px;'},
    {'selector': '.dash-table-container .dash-spreadsheet-container th', 'rule': 'padding: 8px 12px; text-align: center; font-weight:700;'},
    {'selector': '@media (max-width: 900px)', 'rule': 'body { padding: 12px; } .main-container { max-width: 100% !important; padding: 12px !important; }'}
]