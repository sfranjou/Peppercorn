"""CLI: python3 scripts/nds_ui <command> <image config>. See analysis/firmware/NDS_BUILD_SYSTEM.md."""
import sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[2])]
from nds_ui.cli import main
sys.exit(main(sys.argv[1:]))
