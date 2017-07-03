from PIL import Image, ImageDraw
import numpy as np
from PIL import ImageFont

from robotd.vision.tokens import Token


def _draw_centered(pos, text, font, color, dr):
    w, h = dr.textsize(text, font=font)
    x, y = pos[0] - w / 2, pos[1] - h / 2
    dr.text((x+2,y), text, font=font, fill='black')
    dr.text((x-2,y), text, font=font, fill='black')
    dr.text((x,y+2), text, font=font, fill='black')
    dr.text((x,y-2), text, font=font, fill='black')
    dr.text((x,y), text, font=font, fill=color)


def display_tokens(tokens: Token, image: Image):
    new_image = image.convert('RGBA')
    dr = ImageDraw.Draw(new_image)
    fnt = ImageFont.load_default()
    font_size = 28
    try:
        # Pretty font, pretty sure I'm the only one to have it though - Andy
        fnt = ImageFont.truetype("DejaVuSans.ttf", font_size, encoding="unic")
    except:
        try:
            # More common font
            fnt = ImageFont.truetype("arial.ttf", font_size, encoding="unic")
        except:
            print("fallback to default font")
            pass

    token_colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 255, 255),
        (255, 125, 0),
        (0, 255, 255),
    ]

    # Loop the colors if we run out
    token_colors *= int(len(tokens) / len(token_colors))+1

    for token, color in zip(tokens, token_colors):
        corners = token.pixel_corners
        centre = token.pixel_centre
        avg_point = np.mean(corners, axis=0)
        dr.line(corners + [corners[0]], fill=color, width=4)
        ellipse_pos = [(centre[0] - 5, centre[1] - 5), (centre[0] + 5, centre[1] + 5)]
        dr.ellipse(ellipse_pos, fill=color)
        for point in corners:
            ellipse_pos = [(point[0] - 5, point[1] - 5), (point[0] + 5, point[1] + 5)]
            dr.ellipse(ellipse_pos, fill=color)
        _draw_centered((int(avg_point[0]), int(avg_point[1])), str(token.id), fnt, color, dr)
    del dr
    return new_image
