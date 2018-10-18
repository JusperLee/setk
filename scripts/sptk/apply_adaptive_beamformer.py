#!/usr/bin/env python
# coding=utf-8
# wujian@2018
#
"""
Do mvdr/gevd adaptive beamformer
"""

import argparse
import os

import numpy as np
from scipy.io import loadmat

from libs.utils import istft, get_logger, nfft, get_stft_parser
from libs.data_handler import SpectrogramReader, ScriptReader, NumpyReader
from libs.beamformer import MvdrBeamformer, GevdBeamformer

logger = get_logger(__name__)


def run(args):
    stft_kwargs = {
        "frame_length": args.frame_length,
        "frame_shift": args.frame_shift,
        "window": args.window,
        "center": args.center,  # false to comparable with kaldi
        "transpose": False      # F x T
    }
    spectrogram_reader = SpectrogramReader(args.wav_scp, **stft_kwargs)
    mask_reader = NumpyReader(args.mask_scp) if args.numpy else ScriptReader(
        args.mask_scp)

    num_bins = nfft(args.frame_length) // 2 + 1
    beamformer = MvdrBeamformer(
        num_bins) if args.beamformer == "mvdr" else GevdBeamformer(num_bins)

    num_utts = 0
    # why add this good for WER?
    # stft_kwargs['center'] = True
    for key, stft_mat in spectrogram_reader:
        if key in mask_reader:
            num_utts += 1
            norm = spectrogram_reader.samp_norm(key)
            logger.info("Processing utterance {}...".format(key))
            speech_mask = mask_reader[key]
            if args.transpose:
                speech_mask = np.transpose(speech_mask)
            stft_enh = beamformer.run(
                speech_mask, stft_mat, normalize=args.post_filter)
            istft(
                os.path.join(args.dst_dir, '{}.wav'.format(key)),
                stft_enh,
                norm=norm,
                **stft_kwargs)
    logger.info("Processed {:d} utterances out of {:d}".format(
        num_utts, len(spectrogram_reader)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Command to run adaptive(mvdr/gevd) beamformer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[get_stft_parser()])
    parser.add_argument(
        "wav_scp", type=str, help="Multi-channel wave scripts in kaldi format")
    parser.add_argument(
        "mask_scp",
        type=str,
        help=
        "Scripts of masks generated by kaldi's networks(default)/numpy's matrix(add --numpy)"
    )
    parser.add_argument(
        "dst_dir", type=str, help="Location to dump enhanced wave files")
    parser.add_argument(
        "--numpy",
        action="store_true",
        default=False,
        dest="numpy",
        help="Define type of masks in numpy.ndarray instead of kaldi's archives"
    )
    parser.add_argument(
        "--beamformer",
        type=str,
        default="mvdr",
        choices=["mvdr", "gevd"],
        help="Type of beamformer to apply")
    parser.add_argument(
        "--transpose-mask",
        action="store_true",
        default=False,
        dest="transpose",
        help="Shape mask from FxT to TxF(T: num_frames, F: num_bins)")
    parser.add_argument(
        "--post-filter",
        action="store_true",
        default=False,
        dest="post_filter",
        help="Do Blind Analytical Normalization(BAN) or not")
    args = parser.parse_args()
    run(args)
