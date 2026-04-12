"""Common stuff, like ANSI styling."""

base = '\033['

class ANSIStyles:
    """Terminal stylings.
    Color: Foreground, background colors
    Format: Bold, underlines, etc."""
    base = '\033['
    reset = f'{base}0m'
    
    fg_default = f"{base}39m"
    fg_black = f"{base}30m"
    fg_red = f"{base}31m"
    fg_green = f"{base}32m"
    fg_yellow = f"{base}33m"
    fg_blue = f"{base}34m"
    fg_magenta = f"{base}35m"
    fg_cyan = f"{base}36m"
    fg_white = f"{base}37m"
    fg_bright_black = f"{base}90m"
    fg_bright_red = f"{base}91m"
    fg_bright_green = f"{base}92m"
    fg_bright_yellow = f"{base}93m"
    fg_bright_blue = f"{base}94m"
    fg_bright_magenta = f"{base}95m"
    fg_bright_cyan = f"{base}96m"
    fg_bright_white = f"{base}97m"

    bg_default = f"{base}48m"
    bg_black = f"{base}40m"
    bg_red = f"{base}41m"
    bg_green = f"{base}42m"
    bg_yellow = f"{base}43m"
    bg_blue = f"{base}44m"
    bg_magenta = f"{base}45m"
    bg_cyan = f"{base}46m"
    bg_white = f"{base}47m"
    bg_bright_black = f"{base}100m"
    bg_bright_red = f"{base}101m"
    bg_bright_green = f"{base}102m"
    bg_bright_yellow = f"{base}103m"
    bg_bright_blue = f"{base}104m"
    bg_bright_magenta = f"{base}105m"
    bg_bright_cyan = f"{base}106m"
    bg_bright_white = f"{base}107m"
    
    underline = f'{base}4m'
    bold = f'{base}1m'
    faint = f'{base}2m'
    italic = f'{base}3m'
    slowblink = f'{base}5m'
    rapidblink = f'{base}6m'
    bgswap = f'{base}7m'
    conceal = f'{base}8m'
    strikethrough = f'{base}9m'
    underline_off = f'{base}24m'
    blink_off = f'{base}25m'
    inverse_off = f'{base}27m'
    reveal = f'{base}28m'

    ff_disc = f'{base}0;4;32m'
    ff_text = f'{base}0;96m'
    ff_file = f'{base}0;4;95m'
    ff_err = f'{base}0;4;91m'

def fg_color(r, g, b):
    """Sets the foreground color with RGB."""
    return f'\033[38;2;{r};{g};{b}m'

def bg_color(r, g, b):
    """Sets the background color with RGB."""
    return f'\033[48;2;{r};{g};{b}m'