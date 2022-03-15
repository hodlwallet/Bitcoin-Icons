#!/usr/bin/env python

import typer
import os
import sh

from matplotlib import colors
from os import path
from os.path import dirname, abspath
from typer import echo, secho


find = getattr(sh, "find")
cp = getattr(sh, "cp")
rm = getattr(sh, "rm")
inkscape = getattr(sh, "inkscape")


class GenerationError(Exception):
    pass


def parse_color(color: str):
    if color.startswith("#"):
        return color

    if color not in colors.cnames:
        raise GenerationError(
            f"Invalid color: {color}, not found on matplotlib.colors.cnames"
            f", available colors: {', '.join(colors.cnames.keys())}"
        )

    return colors.cnames[color]


def get_complementary_color(color: str) -> str:
    # strip the # from the beginning
    color = color[1:]

    # convert the string into hex
    color_int = int(color, 16)

    # invert the three bytes
    # as good as substracting each of RGB component by 255(FF)
    comp_color = 0xFFFFFF ^ color_int

    # convert the color back to hex by prefixing a #
    comp_color = "#%06X" % comp_color

    # return the result
    return comp_color


def get_root_directory() -> str:
    d = dirname(dirname(abspath(__file__)))

    return d


def get_xamarin_directory(create: bool = True) -> str:
    root = get_root_directory()
    xamarin_path = path.join(root, "xamarin")

    if create and not path.exists(xamarin_path):
        os.makedirs(xamarin_path)

    return xamarin_path


def copy_svg_to_xamarin():
    root = get_root_directory()
    svg = os.path.join(root, "svg")
    xamarin = get_xamarin_directory()

    cp("-r", svg, xamarin)


def replace_color_on_svgs(fill_color_hex: str, stroke_color_hex):
    xamarin = get_xamarin_directory()
    svg_dir = path.join(xamarin, "svg")

    find(
        svg_dir,
        "-name",
        "*.svg",
        "-exec",
        "sed",
        "-i",
        f's/fill="black"/fill="{fill_color_hex}"/g',
        "{}",
        "+",
    )

    find(
        svg_dir,
        "-name",
        "*.svg",
        "-exec",
        "sed",
        "-i",
        f's/stroke="black"/stroke="{stroke_color_hex}"/g',
        "{}",
        "+",
    )


def create_ios_images():
    xamarin = get_xamarin_directory()
    svg = os.path.join(xamarin, "svg")
    ios = os.path.join(xamarin, "ios")

    if not os.path.exists(ios):
        os.makedirs(ios)

    found_files = find(svg, "-name", "*.svg")
    found_files = [found.strip() for found in found_files if found]

    # 1x: 24×24.
    # 2x: 48×48.
    # 4x: 72×72.

    with typer.progressbar(found_files) as progress:
        for svg_file in progress:
            filename = os.path.basename(svg_file)
            no_ext_filename = filename.replace(".svg", "").replace("-", "_")

            if ("svg/filled" in svg_file):
                no_ext_filename = f"filled_{no_ext_filename}"

            png = os.path.join(ios, f"{no_ext_filename}.png")
            png_2x = os.path.join(ios, f"{no_ext_filename}@2x.png")
            png_3x = os.path.join(ios, f"{no_ext_filename}@3x.png")

            inkscape("-w", 24, "-h", 24, svg_file, "-o", png)
            inkscape("-w", 48, "-h", 48, svg_file, "-o", png_2x)
            inkscape("-w", 72, "-h", 72, svg_file, "-o", png_3x)


def create_android_images():
    xamarin = get_xamarin_directory()
    svg = os.path.join(xamarin, "svg")
    android = os.path.join(xamarin, "android")

    if not os.path.exists(android):
        os.makedirs(android)

    drawable = os.path.join(android, "drawable")
    hdpi = os.path.join(android, "drawable-hdpi")
    xhdpi = os.path.join(android, "drawable-xhdpi")
    xxhdpi = os.path.join(android, "drawable-xxhdpi")
    xxxhdpi = os.path.join(android, "drawable-xxxhdpi")

    for a_dir in [drawable, hdpi, xhdpi, xxhdpi, xxxhdpi]:
        if not os.path.exists(a_dir):
            os.makedirs(a_dir)

    found_files = find(svg, "-name", "*.svg")
    found_files = [found.strip() for found in found_files if found]

    # These are all but we gonna do only 3, ldpi, hdpi and xhdpi
    #
    # drawable: 60x60
    # mdpi: 48×48.
    # hdpi: 72×72.
    # xhdpi: 96×96.
    # xxhdpi: 144×144.
    # xxxhdpi: 192×192.

    with typer.progressbar(found_files) as progress:
        for svg_file in progress:
            filename = os.path.basename(svg_file)
            no_ext_filename = filename.replace(".svg", "").replace("-", "_")

            drawable_png = os.path.join(drawable, f"{no_ext_filename}.png")
            hdpi_png = os.path.join(hdpi, f"{no_ext_filename}.png")
            xhdpi_png = os.path.join(xhdpi, f"{no_ext_filename}.png")
            xxhdpi_png = os.path.join(xxhdpi, f"{no_ext_filename}.png")
            xxxhdpi_png = os.path.join(xxxhdpi, f"{no_ext_filename}.png")

            inkscape("-w", 60, "-h", 60, svg_file, "-o", drawable_png)
            inkscape("-w", 48, "-h", 48, svg_file, "-o", hdpi_png)
            inkscape("-w", 64, "-h", 64, svg_file, "-o", xhdpi_png)
            inkscape("-w", 96, "-h", 96, svg_file, "-o", xxhdpi_png)
            inkscape("-w", 128, "-h", 128, svg_file, "-o", xxxhdpi_png)


def color_too_bright(color: str) -> bool:
    color_hex = parse_color(color)
    color_hex = color_hex[1:]

    c_r = int(color_hex[:2], 16)
    c_b = int(color_hex[2:4], 16)
    c_g = int(color_hex[4:], 16)

    brightness = ((c_r * 299) + (c_g * 587) + (c_b * 114)) / 1000

    return brightness > 155


def cleanup():
    xamarin = get_xamarin_directory(create=False)

    if os.path.exists(xamarin):
        rm("-rf", xamarin)


def generate_images(fill_color: str, stroke_color: str):
    root = get_root_directory()

    fill_color_hex = parse_color(fill_color)
    stroke_color_hex = parse_color(stroke_color)

    fg_color = "black" if color_too_bright(fill_color) else "white"
    comp_color = get_complementary_color(fill_color_hex)

    echo("Color selected: ", nl=False)

    try:
        secho(f"{fill_color}", bg=fill_color, fg=fg_color, nl=False)
    except TypeError:
        echo(f"{fill_color}", nl=False)

    echo(f" ({fill_color_hex}, complementary: {comp_color})")
    echo(f"Running on directory: {root}")

    cleanup()
    copy_svg_to_xamarin()
    replace_color_on_svgs(fill_color_hex, stroke_color_hex)

    echo("Creating iOS images please wait...")
    create_ios_images()
    secho("done.", fg="green")

    echo("Creating Android images please wait...")
    create_android_images()
    secho("done.", fg="green")


def main(fill_color: str = "black", stroke_color: str = "black"):
    """
    Generates all needed files for importing as png
    in a specific color, using inkscape and regexes
    replaces to archive all that.
    """
    secho(
        "Generating icons for iOS and Android to be useable on Xamarin Forms...",
        fg="green",
    )

    generate_images(fill_color, stroke_color)


if __name__ == "__main__":
    typer.run(main)
