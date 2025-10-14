from math import pi, sin, cos, log
from wave import open as waveopen
from random import gauss, uniform, seed
from os import makedirs

# Harmonics frequencies relative to the fundamental are brought to the
# timbre/12 power. 12 is natural, higher numbers are round, lower numbers
# are concave.
# Harmonics are snapped to standard keyboard positions. Timbres of 12, 10, and 15 have
# particularly low amounts of snap needed.
# See https://docs.google.com/spreadsheets/d/1PjRy3Nx4hvH13SmmNt9huLVwYWwTtVzQYKkRoF7oD-8/edit
timbre = 12
# The audio level. Should be just shy of what will overblow the output for the timbre
level = 1.4
# 44100 is CD standard
sample_rate = 44100
# Output sample length in seconds
sample_length = 10
# The rate of decay of the first harmonic, still subject to harmonic_falloff_exponent
base_decay = 0.6
# What exponent to bring the harmonic number to when calculating the
# falloff rate. 1 is idealized plucked string, 0 is completely flat
harmonic_falloff_exponent = 0.5
# If this is set to 0 the attack starts with a pure sine wave
initial_fuzz = 2
# The units of this interact with the sample rate. Ideally it would be
# applied in a way which made changing the sample rate not alter the tone
noise_level = 0.01
# How quickly the amount of fuzz expands. Emulates an effect which happens
# when a physical string is plucked
fuzz_expansion_rate = 1
# The duration in which to go to 0 volume at the end
tamper_interval = 0.2

def prime_factorization(n):
    r = []
    v = n
    for i in range(2, n+1):
        while v % n == 0:
            v /= n
            r.append(n)
    return r

def snap_halftone(v):
    return round(12*log(v)/log(2))

def stretch_single_harmonic(h, stretch):
    v = sum(snap_halftone(x**(stretch/12)) for x in prime_factorization(h))
    return 2 ** (v/12)

def make_clean_note(frequency, num_samples):
    phase = uniform(0, 2*pi)
    r = []
    for i in range(num_samples):
        t = i / sample_rate
        phase += frequency * (2 ** ((t*fuzz_expansion_rate+initial_fuzz) * gauss(0, noise_level))) * 2 * pi / sample_rate
        r.append(sin(phase))
    return r

def make_clean_whole_note(frequency, num_samples):
    print('whole note', frequency)
    result = [0] * num_samples
    # The standard strike point of a real piano is 1/8 up the string which
    # is generalized to three octaves here
    real_octave = stretch_single_harmonic(8, timbre)
    # Higher harmonics are generally inaudible
    for h_base in range(1, 41):
        h_base = stretch_single_harmonic(h_base, timbre)
        # Squaring for the amplitude is the idealized value. Human ears
        # are very sensitive to this being off
        amplitude = sin(h_base*pi/real_octave)/(h_base ** 2)
        # cutoff at human hearing levels
        if frequency * h_base < 20000:
            new_samples = make_clean_note(frequency * h_base, num_samples)
            for i in range(num_samples):
                result[i] += amplitude * new_samples[i] * (base_decay ** (h_base * harmonic_falloff_exponent * i / sample_rate)) * level
    for i, v in enumerate(result):
        result[i] = apply_envelope(v, i/sample_rate, num_samples/sample_rate)
    return remove_pops(result)

def apply_envelope(v, t, duration):
    return v * cosine_tamp((t - duration + tamper_interval) / tamper_interval)

def cosine_tamp(t):
    if t < 0:
        return 1
    if t > 1:
        return 0
    return (1 + cos(pi * t)) / 2

def remove_pops(result):
    begin = 0
    sign = result[begin] > 0
    while result[begin] != 0 and (result[begin] > 0) == sign:
        begin += 1
    sign = (result[-1] > 0)
    end = -1
    while result[end] != 0 and (result[end-1] > 0) == sign:
        end -= 1
    m = max(abs(x) for x in result)
    print('max', m)
    if m >= 1:
        return None
    histogram = [0] * 10
    for v in result:
        histogram[int(abs(v*10))] += 1
    print(histogram)
    return result[begin:end]

def convert_wav_data(vals):
    frames = []
    for a in vals:
        frames.append(int(a*(2**15)).to_bytes(length = 2, byteorder = 'little', signed=True) +
            int(-a*(2**15)).to_bytes(length = 2, byteorder = 'little', signed=True))
    return b''.join(frames)

def make_wav_file(filename, wavedata, rate):
    f = waveopen(filename, 'wb')
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(rate)
    f.writeframes(wavedata)
    f.close()

# Between when the notes were given names and when they were given numbers the
# fashion in composing when from minor key to major key, hence the weird names
note_names = [
    'A0', 'Bb0', 'B0',
    'C1', 'Db1', 'D1', 'Eb1', 'E1', 'F1', 'Gb1', 'G1', 'Ab1', 'A1', 'Bb1', 'B1',
    'C2', 'Db2', 'D2', 'Eb2', 'E2', 'F2', 'Gb2', 'G2', 'Ab2', 'A2', 'Bb2', 'B2',
    'C3', 'Db3', 'D3', 'Eb3', 'E3', 'F3', 'Gb3', 'G3', 'Ab3', 'A3', 'Bb3', 'B3',
    'C4', 'Db4', 'D4', 'Eb4', 'E4', 'F4', 'Gb4', 'G4', 'Ab4', 'A4', 'Bb4', 'B4',
    'C5', 'Db5', 'D5', 'Eb5', 'E5', 'F5', 'Gb5', 'G5', 'Ab5', 'A5', 'Bb5', 'B5',
    'C6', 'Db6', 'D6', 'Eb6', 'E6', 'F6', 'Gb6', 'G6', 'Ab6', 'A6', 'Bb6', 'B6',
    'C7', 'Db7', 'D7', 'Eb7', 'E7', 'F7', 'Gb7', 'G7', 'Ab7', 'A7', 'Bb7', 'B7',
    'C8',
]

def make_all_notes():
    for i in range(0, len(note_names)):
        note_name = note_names[i]
        print(f'making {i} timbre{timbre}_{note_name}.wav')
        seed_root = 3
        while True:
            seed(seed_root)
            # standard piano note positions
            data = make_clean_whole_note((2 ** (i/12)) * 440 / 16, sample_rate * sample_length)
            # If the volume of this run blew the limit, redo it
            if data is None:
                seed_root += 1
                continue
            make_wav_file(f'Samples/timbre{timbre}_{note_name}.wav', convert_wav_data(data), sample_rate)
            break

def make_timbres():
    makedirs('Samples', exist_ok=True)
    global timbre
    global level
    make_all_notes()
    timbre = 15
    level = 2.5
    make_all_notes()
    timbre = 10
    level = 0.95
    make_all_notes()

make_timbres()
