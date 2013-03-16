#/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Sounds of Ocean Color
'''

from StringIO import StringIO
from bisect import bisect

import numpy as np
from pyknon.simplemusic import mod12, notes_names, name_to_number
from pyknon.genmidi import Midi, NoteSeq


def lin_interp(self):
    """
    Interp values discarding NaN.

    Parameter
    ------------
    self: 1d numpy array with NaN's

    Returns
    -----------
    nans: (índex of NANs)
    index: (x), a function over the index, converting
          logical indices of NaNs to values of indices.
    """
    nans, x = np.isnan(self), lambda z: z.nonzero()[0]
    self[nans] = np.interp(x(nans), x(~nans), self[~nans])


def classe_notas(arr):
    a = np.nanmax(arr)
    notes_class = np.arange(0, a, a / 12.)
    return notes_class


def note_number(arr):
    x_notes = classe_notas(arr)
    mapping = np.asarray([bisect(x_notes, a) for a in arr]) - 1
    mapping[np.isnan(arr)] = np.nan
    return mapping


def set_scale(note, arr, mode='major'):
    '''
    mode = 'major'
    C,C#,D,D#,E,F,F#,G,G#,A,A#,B,C
    0,1, 2,3, 4,5,6, 7,8, 9,10,11,12

    # Maior
    [1, 1, 1/2, 1, 1, 1, 1/2]
    C,D,  E, F,G,A, B,C
    0  2,  4, 5,7,9,11,12
    D,E, F#, G,A,B ,C#,D
    2, 4, 6, 7,9,11,1,2

    mode = 'minor'
    0,1, 2,3, 4,5,6, 7,8, 9,10,11,12
    C,C#,D,D#,E,F,F#,G,G#,A,A#,B,C

    # Menor
    [1, 1/2, 1, 1, 1/2, 1, 1]
    C, D, D#, F, G, G#, A#, C
    0, 2, 3,  5, 7, 8, 10 ,12
    D, E, F,  G,  A, A#, C, D
    2, 4, 5,  7,  9,10, 12, 2
    '''
    note = mod12(note)
    major_disp = np.array([0, 2, 4, 5, 7, 9, 11, 12])
    minor_disp = np.array([0, 2, 3, 5, 7, 8, 10, 12])
    scale_class = np.arange(0, np.nanmax(arr), np.nanmax(arr) / 8.)
    if mode == 'major':
        mj = mod12(major_disp + note)
    elif mode == 'minor':
        mj = mod12(minor_disp + note)

    mapping = np.asarray([mj[bisect(scale_class, a) - 1] for a in arr])
    mapping[np.isnan(arr)] = np.nan
    return mapping


def note_name_nan(number):
    '''
    Transform a number to a note string, including
    np.nan as musical rests.
    This function is based on the acronym of "pyknon" function
    without NaN.
    '''
    notes = "C C# D D# E F F# G G# A A# B".split()
    rest = "R"
    if np.isnan(number):
        name = rest
    elif number < (-2000000000.):
        name = rest
    else:
        name = notes[mod12(number)]
    return name


def notes_names_nan(notes):
    '''
    Transform an array of multiple numeric values to note
    strings, considering the function called inside (note_name_nan)
    '''
    return [note_name_nan(x) for x in notes]


def scale_of_year(arr, mode='major'):
    '''
    Parameters
    ----------------
    arr: is an array
    mode: may be a 'major' or 'minor'

    Return
    ----------------
    x: Mean note of time series referenced by scale.
    y: Array scaled based on Mean Note.
    z: Year Scale

    '''
    arr = np.asarray(arr)
    major_disp = np.array([0, 2, 4, 5, 7, 9, 11, 12])
    minor_disp = np.array([0, 2, 3, 5, 7, 8, 10, 12])
    if len(arr) == 1:
        val = arr
        val_mean = set_scale(arr, arr, mode)
    else:
        arr_mean = np.nansum(arr) / len(arr)
        val = set_scale(arr_mean, arr, mode)
        val_mean = np.nansum(val) / len(val)

    if mode == 'major':
        mj = mod12(major_disp + val_mean)
    elif mode == 'minor':
        mj = mod12(minor_disp + val_mean)
    year_notes = notes_names(np.int32(mj))
    return val_mean, val, ' '.join(year_notes)


def chord_scaled(arr):
    '''
    Create chords based on the mean values of each anual time series.
    Based on the scale of the year and harmonized trough pyknon module.

    Parameters
    -------------
    arr: Pixel time series

    Returns
    -------------
    chords: a list of chords
    rest_chords: a list of NoteSeq chords, including rests.
    '''
    am_x, am_y, am_z = scale_of_year(arr, mode='major')
    scale = NoteSeq(am_z)
    scale_numbers = [name_to_number(i) for i in am_z.split(' ')]
    arr_scaled = np.int32([np.nansum(row) / len(row) for row in
                           am_y.reshape((-1, 12))])
    mean_years_fig = NoteSeq(' '.join(notes_names(arr_scaled)))
    chords = []
    rest_chords = []
    for i, j in enumerate(mean_years_fig):
    ## check if note "j" is on the primary musical scale
        if not j in scale:
            # FIX THIS!!
            #note = arr_scaled(i)
            #aq_x, aq_y, aq_z = scale_of_year(np.ndarray(arr_scaled(i)), mode)
            #scale = NoteSeq(aq_z)
            scale = scale.transposition(1)
        chords.append(NoteSeq(j.harmonize(scale)))
        scale = NoteSeq(am_z)

    for qq in chords:
        rest_chords.append(qq)
        for i in range(12):
            rest_chords.append(NoteSeq('R'))

    return chords, rest_chords


def get_music(am, name='am'):
    ######### Get Music  ##########
    xx, yy = chord_scaled(am.copy())

    am_notes = note_number(am.copy())
    am_fig = notes_names_nan(np.int32(am_notes))

    # Transform it to a MIDI file with chords.
    am_musiq = ' '.join(am_fig)

    midi_out = StringIO()
    am_musiq_midi = NoteSeq(am_musiq)
    midi = Midi(1, tempo=200)
    midi.seq_notes(am_musiq_midi, track=0)
    midi.seq_chords(yy, track=0)
    #midi.write("%s_cbo_select_music.mid" % name)
    midi.write(midi_out)

    return midi_out
'''
    # Transform it to a MIDI file.
    am_musiq = ' '.join(am_fig)

    am_musiq_midi = NoteSeq(am_musiq)
    midi = Midi(1, tempo=120)
    midi.seq_notes(am_musiq_midi,track=0)
    midi.seq_notes(retrograde(am_musiq_midi),track=0)
    midi.write("%s_sound_nan_retrograde.mid" % name)

    # Music with "Rests" on NaN's
    am_fig_nan = notes_names_nan(np.int32(am_notes))
    am_musiq = ' '.join(am_fig_nan)

    am_musiq_midi = NoteSeq(am_musiq)
    midi = Midi(1, tempo=150)
    midi.seq_notes(am_musiq_midi,track=0)
    midi.write("%s_sound_nan.mid" % name)

    # Music Major scaled
    am_scaled = set_scale(3, am, mode = 'major')
    am_scaled_fig = notes_names_nan(np.int32(am_scaled))

    am_scaled_musiq = ' '.join(am_scaled_fig)
    am_scaled_musiq_midi = NoteSeq(am_scaled_musiq)
    midi = Midi(1, tempo = 120)
    midi.seq_notes(am_scaled_musiq_midi, track=0)
    midi.write("%s_scaled_major.mid" % name)

    #Music Minor scaled
    am_scaled = set_scale(3, am, mode = 'minor')
    am_scaled_fig = notes_names_nan(np.int32(am_scaled))

    am_scaled_musiq = ' '.join(am_scaled_fig)
    am_scaled_musiq_midi = NoteSeq(am_scaled_musiq)
    midi = Midi(1, tempo = 120)
    midi.seq_notes(am_scaled_musiq_midi, track=0)
    midi.write("%s_scaled_minor.mid" % name)
'''
