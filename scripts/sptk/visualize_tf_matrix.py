#!/usr/bin/env python
# coding=utf-8
# wujian@2018

import glob
import argparse

import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from libs.data_handler import ScriptReader, ArchiveReader
from libs.utils import get_logger, filekey
from libs.opts import StrToBoolAction

default_font = "Times New Roman"
default_dpi = 200
default_fmt = "jpg"

logger = get_logger(__name__)


class NumpyReader(object):
    """
    Simple directory reader for .npy objects
    """
    def __init__(self, src_dir):
        src_dir = Path(src_dir)
        if not src_dir.is_dir():
            raise RuntimeError("NumpyReader expect dir as input")
        flist = glob.glob((src_dir / "*.npy").as_posix())
        self.index_dict = {filekey(f): f for f in flist}

    def __iter__(self):
        for key, path in self.index_dict.items():
            yield key, np.load(path)


def save_figure(key,
                mat,
                dest,
                cmap="jet",
                hop=256,
                sr=16000,
                title="",
                size=3):
    """
    Save figure to disk
    """
    def plot(mat, num_frames, num_bins, xticks=True):
        plt.imshow(np.transpose(mat),
                   origin="lower",
                   cmap=cmap,
                   aspect="auto",
                   interpolation="none")
        if xticks:
            xp = np.linspace(0, num_frames - 1, 5)
            plt.xticks(xp, [f"{t:.2f}" for t in (xp * hop * 1e3 / sr)],
                       fontproperties=default_font)
            plt.xlabel("Time(s)", fontdict={"family": default_font})
        else:
            # disble xticks
            plt.xticks([])
        yp = np.linspace(0, num_bins - 1, 6)
        fs = np.linspace(0, sr / 2, 6) / 1000
        plt.yticks(yp, [f"{t:.1f}" for t in fs], fontproperties=default_font)
        plt.ylabel("Frequency(kHz)", fontdict={"family": default_font})

    logger.info(f"Plot TF-mask of utterance {key} to {dest}.{default_fmt}...")
    if mat.ndim == 3:
        N, T, F = mat.shape
    else:
        T, F = mat.shape
        N = 1
    plt.figure(figsize=(max(size * T / F, size) + 2, size + 2))
    if N != 1:
        ts = title.split(";")
        for i in range(N):
            plt.subplot(int(f"{N}1{i + 1}"))
            plot(mat[i], T, F, xticks=i == N - 1)
            plt.title(ts[i] if len(ts) == N else title,
                      fontdict={"family": default_font})
    else:
        plot(mat, T, F)
        plt.title(title, fontdict={"family": default_font})
    plt.savefig(f"{dest}.{default_fmt}", dpi=default_dpi, format=default_fmt)
    plt.close()


def run(args):
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    reader_templ = {
        "dir": NumpyReader,
        "scp": ScriptReader,
        "ark": ArchiveReader
    }
    # ndarrays or archives
    mat_reader = reader_templ[args.input](args.rspec)
    for key, mat in mat_reader:
        if mat.ndim == 3 and args.index >= 0:
            mat = mat[args.index]
        if args.apply_log:
            mat = np.log10(mat)
        if args.trans:
            mat = np.swapaxes(mat, -1, -2)
        if args.norm:
            mat = mat / np.max(np.abs(mat))
        save_figure(key,
                    mat,
                    cache_dir / key.replace(".", "-"),
                    cmap=args.cmap,
                    hop=args.frame_hop * 1e-3,
                    sr=args.sr,
                    size=args.size,
                    title=args.title)


# now support input from stdin
# shuf mask.scp | head | copy-feats scp:- ark:- | ./scripts/sptk/visualize_tf_matrix.py -
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        "Command to visualize kaldi's features/numpy's ndarray on T-F domain. "
        "egs: spectral/spatial features or T-F mask. ",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("rspec",
                        type=str,
                        help="Read specifier of archives "
                        "or directory of ndarrays")
    parser.add_argument("--input",
                        type=str,
                        choices=["ark", "scp", "dir"],
                        default="dir",
                        help="Type of the input read specifier")
    parser.add_argument("--frame-hop",
                        type=int,
                        default=256,
                        help="Frame shift in samples")
    parser.add_argument("--sr",
                        type=int,
                        default=16000,
                        help="Sample frequency (Hz)")
    parser.add_argument("--cache-dir",
                        type=str,
                        default="figure",
                        help="Directory to cache pictures")
    parser.add_argument("--apply-log",
                        action=StrToBoolAction,
                        default=False,
                        help="Apply log on input features")
    parser.add_argument("--trans",
                        action=StrToBoolAction,
                        default=False,
                        help="Apply matrix transpose on input features")
    parser.add_argument("--norm",
                        action=StrToBoolAction,
                        default=False,
                        help="Normalize values in [-1, 1] "
                        "before visualization")
    parser.add_argument("--cmap",
                        choices=["binary", "jet", "hot"],
                        default="jet",
                        help="Colormap used when save figures")
    parser.add_argument("--size",
                        type=int,
                        default=3,
                        help="Minimum height of images (in inches)")
    parser.add_argument("--index",
                        type=int,
                        default=-1,
                        help="Channel index to plot, -1 means all")
    parser.add_argument("--title",
                        type=str,
                        default="",
                        help="Title of the pictures")
    args = parser.parse_args()
    run(args)
