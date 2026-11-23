"""Let binutils honor NDS32 code/data mapping symbols in relocated sections.

nds32-dis.c only consults $c/$d mapping symbols in sections named .text*.
Use a separate ELF view with renamed executable sections; never alter the link.
"""
import subprocess


def mapped_view(elf, sections, objcopy):
    view = elf.with_suffix('.disassembly')
    names = {name: '.text' + name for name in sections if not name.startswith('.text')}
    args = [str(objcopy)]
    for old, new in names.items():
        args += ['--rename-section', old + '=' + new]
    subprocess.run(args + [str(elf), str(view)], check=True)
    return view, {name: names.get(name, name) for name in sections}
