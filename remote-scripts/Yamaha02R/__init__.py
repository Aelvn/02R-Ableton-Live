# -*- coding: utf-8 -*-
# Remote Script Ableton Live 12 - Yamaha 02R V2 (couche Remote, cible General MIDI)
# Version 13
# Fenetre d'etat : envoie banque, mode, pistes et potards (modes EQ/Retour/Plugin) en UDP (127.0.0.1:9002) a Fenetre02R.ps1
#
# Faders 1-16  : volume (retour moteurs)
# Potards 1-16 : Pan / Send A / Send B / Send C / EQ / Retour A / B / C
# ON 1-16      : mute (le voyant de la console fait foi)
# SEL 1-16     : selectionne la piste + MixHub + potards en mode EQ
# SEL double appui         : arme la piste en enregistrement
# NUMEROTATION PHYSIQUE DE LA CONSOLE (les voies 17-18 sont stereo et hors serie) :
#   ON 19 = banque precedente   (adresse 00 67, "BTN 17" dans le code)
#   ON 20 = banque suivante     (adresse 00 77, "BTN 18" dans le code)
#   ON 21 = mode des potards    (adresse 01 07, "BTN 19" dans le code)
#   ON du MASTER = Shift        (adresse 01 2F, SHIFT_ADDR dans le code)
# ON Master maintenu + SEL     : solo de la piste
# ON Master maintenu + potards : 2e page de reglages (EQ et retours : reglages 17 a 32)
# Molette (1A 57)          : reglage fin du dernier reglage touche
# Fleches / ON 19 / ON 20  : banques (ON Master maintenu = 1 piste)
# ON Master seul : piste 1 | ON Master + ON 21 : suivi de selection
# LOW/HPF, L-MID, H-MID, HIGH/LPF : EQ, Retour A, Retour B, Retour C
# ON de la section EQUALIZER : potards sur le PLUGIN SELECTIONNE dans Ableton (tout VST)
# Alerte dans la barre d'etat si un voyant ON ne correspond plus au mute Ableton

import time
import json
import socket
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_CC_TYPE

DEBUG = False  # True = affiche chaque SysEx recu dans la barre d'etat

NUM_STRIPS = 16
CC_VOL = 7
CC_KNOB = 10
IGNORE_WINDOW = 0.4
DOUBLE_PRESS = 0.4      # secondes pour un double appui sur SEL
PAGE_SIZE = 16          # 2e page des potards avec Shift
STATUS_PORT = 9002       # port de la fenetre d'etat (Fenetre02R.ps1)
FINE_STEPS = 500        # nombre de crans de molette pour parcourir un reglage
MODE_NAMES = ["Pan", "Send A", "Send B", "Send C", "EQ",
              "Retour A", "Retour B", "Retour C", "Plugin"]
MODE_EQ = 4
MODE_RET_A = 5  # Retour A = 5, B = 6, C = 7
MODE_DEV = 8    # Plugin selectionne dans Ableton
# Modes Retour : potard n = n-ieme reglage configure du 1er plugin de la piste de retour
EQ_NAME_KEYS = ("MIXHUB", "SSL")
EQ_ON_SLOT = 16  # 17e parametre configure (index 16 apres "Device On")

# Potard console n = n-ieme reglage configure dans le MixHub (Mono et Stereo) :
#  1 HPF, 2 LPF, 3 LF freq, 4 LF dB, 5 LMF Q, 6 LMF freq, 7 LMF dB,
#  8 HMF Q, 9 HMF freq, 10 HMF dB, 11 HF freq, 12 HF dB,
#  13 Output, 14 Threshold, 15 Ratio, 16 Comp mix
EQ_KNOB_ORDER = list(range(1, 17))

BTN_LEFT = 17
BTN_RIGHT = 18
BTN_MODE = 19
BTN_SHIFT = 20

ARROW_LEFT = (0x01, 0x3A)
ARROW_RIGHT = (0x01, 0x2A)

# Section EQUALIZER de la console
# Boutons de bande -> acces direct aux pages
EQ_BAND_BUTTONS = {
    (0x01, 0x3C): 4,  # LOW/HPF  -> EQ (MixHub)
    (0x01, 0x3D): 5,  # L-MID    -> Retour A
    (0x01, 0x3E): 6,  # H-MID    -> Retour B
    (0x01, 0x3F): 7,  # HIGH/LPF -> Retour C
}
EQ_ON_BUTTON = (0x01, 0x1E)

# Touche Shift = ON du Master de la console (adresse relevee : 01 2F)
SHIFT_ADDR = (0x01, 0x2F)


# fin d'adresse -> (type de bouton, premier numero de la serie)
_BUTTON_SERIES = {3: ("on", 1), 7: ("on", 11), 2: ("sel", 1), 6: ("sel", 11)}


def decode_button(hi, lo):
    """Adresse SysEx -> ("on" ou "sel", numero 1-20), ou (None, None)."""
    a = (hi << 7) | lo
    r = a % 16
    if r not in _BUTTON_SERIES:
        return None, None
    kind, first = _BUTTON_SERIES[r]
    n = (a - r) // 16 + first
    return (kind, n) if 1 <= n <= 20 else (None, None)


def midi_to_pan(v):
    return (v - 64) / 63.0 if v >= 64 else (v - 64) / 64.0


def pan_to_midi(p):
    v = 64 + p * 63.0 if p >= 0 else 64 + p * 64.0
    return max(0, min(127, int(round(v))))


def param_to_midi(param):
    rng = param.max - param.min
    return int(round((param.value - param.min) / rng * 127)) if rng else 0


def midi_to_param(param, v):
    val = param.min + (param.max - param.min) * v / 127.0
    if param.is_quantized:
        val = round(val)
    return val


# Calage des faders : repere 0 de la console (valeur 103) = 0 dB dans Ableton
CONSOLE_0DB = 103      # valeur envoyee par la 02R sur son repere 0
LIVE_0DB = 0.85        # position normalisee du 0 dB d'Ableton (1.0 = +6 dB)


def cc_to_vol(param, v):
    if v <= CONSOLE_0DB:
        norm = LIVE_0DB * v / float(CONSOLE_0DB)
    else:
        norm = LIVE_0DB + (1.0 - LIVE_0DB) * (v - CONSOLE_0DB) / float(127 - CONSOLE_0DB)
    return param.min + (param.max - param.min) * norm


def vol_to_cc(param):
    rng = param.max - param.min
    norm = (param.value - param.min) / rng if rng else 0.0
    if norm <= LIVE_0DB:
        v = norm / LIVE_0DB * CONSOLE_0DB
    else:
        v = CONSOLE_0DB + (norm - LIVE_0DB) / (1.0 - LIVE_0DB) * (127 - CONSOLE_0DB)
    return max(0, min(127, int(round(v))))


class Yamaha02R(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._offset = 0
        self._mode = 0
        self._follow = True
        self._shift_held = False
        self._shift_used = False
        self._ignore_until = [0.0] * NUM_STRIPS
        self._last_vol = [None] * NUM_STRIPS
        self._last_knob = [None] * NUM_STRIPS
        self._bound = []
        self._dev_track = None
        self._console_on = [True] * NUM_STRIPS   # etat des voyants ON de la console
        self._last_sel = (None, 0.0)
        self._page = 0
        self._last_touched = None
        with self.component_guard():
            self._controls_02r = []
            for ch in range(NUM_STRIPS):
                vol = SliderElement(MIDI_CC_TYPE, ch, CC_VOL)
                knob = SliderElement(MIDI_CC_TYPE, ch, CC_KNOB)
                vol.add_value_listener(self._make_vol_in(ch))
                knob.add_value_listener(self._make_knob_in(ch))
                self._controls_02r.append((vol, knob))
        self.song().add_tracks_listener(self._on_tracks_changed)
        self.song().view.add_selected_track_listener(self._on_selected_track)
        self._watch_devices()
        self._rebind()
        self._last_state = None
        self._last_state_time = 0.0
        try:
            self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception:
            self._udp = None
        self.log_message("Yamaha02R v13 : script charge")

    # ---------- utilitaires ----------
    def _tracks(self):
        return list(self.song().tracks)

    def _track(self, ch):
        tracks = self._tracks()
        i = self._offset + ch
        return tracks[i] if i < len(tracks) else None

    def _eq_device(self):
        track = self.song().view.selected_track
        try:
            for d in track.devices:
                name = d.name.upper()
                if any(k in name for k in EQ_NAME_KEYS):
                    return d
        except Exception:
            pass
        return None

    def _knob_param(self, ch):
        if self._mode == MODE_EQ:
            dev = self._eq_device()
            if dev is None:
                return None
            params = list(dev.parameters)[1:]  # on saute "Device On"
            i = EQ_KNOB_ORDER[ch] - 1 + self._page * PAGE_SIZE
            return params[i] if i < len(params) else None
        if self._mode == MODE_DEV:
            dev = self._selected_device()
            if dev is None:
                return None
            params = list(dev.parameters)[1:]  # on saute "Device On"
            i = ch + self._page * PAGE_SIZE
            return params[i] if i < len(params) else None
        if MODE_RET_A <= self._mode < MODE_RET_A + 3:
            dev = self._return_device(self._mode - MODE_RET_A)
            if dev is None:
                return None
            params = list(dev.parameters)[1:]  # on saute "Device On"
            i = ch + self._page * PAGE_SIZE
            return params[i] if i < len(params) else None
        track = self._track(ch)
        if track is None:
            return None
        if self._mode == 0:
            return track.mixer_device.panning
        sends = track.mixer_device.sends
        i = self._mode - 1
        return sends[i] if i < len(sends) else None

    def _selected_device(self):
        try:
            return self.song().view.selected_track.view.selected_device
        except Exception:
            return None

    def _return_device(self, i):
        returns = list(self.song().return_tracks)
        if i >= len(returns):
            return None
        devices = list(returns[i].devices)
        return devices[0] if devices else None

    def _mode_text(self):
        mode = MODE_NAMES[self._mode]
        if self._mode == MODE_EQ:
            dev = self._eq_device()
            mode += " (%s)" % (dev.name if dev else "aucun MixHub/SSL sur la piste")
        elif self._mode == MODE_DEV:
            dev = self._selected_device()
            mode += " (%s)" % (dev.name if dev else "clique sur un plugin dans Ableton")
        elif MODE_RET_A <= self._mode < MODE_RET_A + 3:
            dev = self._return_device(self._mode - MODE_RET_A)
            mode += " (%s)" % (dev.name if dev else "pas de plugin sur ce retour")
        if self._page:
            mode += " page 2"
        return mode

    def _status(self):
        first = self._offset + 1
        mode = self._mode_text()
        msg = ("02R : pistes %d-%d | Potards : %s | Suivi : %s"
               % (first, first + NUM_STRIPS - 1, mode, "ON" if self._follow else "OFF"))
        bad = self._mute_mismatch()
        if bad:
            msg += " | ATTENTION voyants ON decales voies %s" % ", ".join(str(x) for x in bad)
        self.show_message(msg)

    # ---------- fenetre d'etat ----------
    def _send_state(self):
        if getattr(self, "_udp", None) is None:
            return
        try:
            tracks = self._tracks()
            sel = self.song().view.selected_track
            strips = []
            for ch in range(NUM_STRIPS):
                i = self._offset + ch
                if i < len(tracks):
                    t = tracks[i]
                    arm = False
                    try:
                        arm = bool(t.can_be_armed and t.arm)
                    except Exception:
                        pass
                    strips.append({"num": i + 1, "name": t.name,
                                   "color": "#%06X" % (t.color & 0xFFFFFF),
                                   "mute": bool(t.mute), "arm": arm,
                                   "sel": t == sel})
                else:
                    strips.append({"num": i + 1, "name": ""})
            knobs = []
            if self._mode >= MODE_EQ:
                for ch in range(NUM_STRIPS):
                    try:
                        prm = self._knob_param(ch)
                    except Exception:
                        prm = None
                    if prm is None:
                        knobs.append({"name": ""})
                        continue
                    rng = prm.max - prm.min
                    norm = (prm.value - prm.min) / rng if rng else 0.0
                    try:
                        txt = prm.str_for_value(prm.value)
                    except Exception:
                        txt = "%.2f" % prm.value
                    knobs.append({"name": prm.name, "value": txt,
                                  "norm": round(max(0.0, min(1.0, norm)), 3)})
            state = {"first": self._offset + 1,
                     "view": "knobs" if self._mode >= MODE_EQ else "tracks",
                     "modeidx": self._mode,
                     "page": self._page,
                     "knobs": knobs,
                     "last": self._offset + NUM_STRIPS,
                     "mode": self._mode_text(),
                     "shift": bool(self._shift_held),
                     "follow": bool(self._follow),
                     "alert": ", ".join(str(x) for x in self._mute_mismatch()),
                     "strips": strips}
            data = json.dumps(state)
            now = time.time()
            # envoi a chaque changement, et toutes les 2 s pour une fenetre ouverte apres Ableton
            if data != self._last_state or now - self._last_state_time > 2.0:
                self._last_state = data
                self._last_state_time = now
                self._udp.sendto(data.encode("utf-8"), ("127.0.0.1", STATUS_PORT))
        except Exception:
            pass

    def update_display(self):
        ControlSurface.update_display(self)
        self._send_state()

    def _mute_mismatch(self):
        bad = []
        for ch in range(NUM_STRIPS):
            track = self._track(ch)
            if track is not None and track.mute != (not self._console_on[ch]):
                bad.append(ch + 1)
        return bad

    def _move_to(self, new_offset):
        count = len(self._tracks())
        new_offset = max(0, min(new_offset, max(0, count - 1)))
        if new_offset != self._offset:
            self._offset = new_offset
            self._rebind()
        self._status()

    def _shift(self, delta):
        target = self._offset + delta
        if delta > 0 and target >= len(self._tracks()):
            self._status()
            return
        self._move_to(target)

    # ---------- console -> Live ----------
    def _make_vol_in(self, ch):
        def cb(value):
            if time.time() < self._ignore_until[ch]:
                return
            track = self._track(ch)
            if track is None:
                return
            self._last_vol[ch] = value
            p = track.mixer_device.volume
            p.value = cc_to_vol(p, value)
            self._last_touched = p
        return cb

    def _make_knob_in(self, ch):
        def cb(value):
            p = self._knob_param(ch)
            if p is None or not p.is_enabled:
                return
            if self._shift_held:
                self._shift_used = True
            self._last_knob[ch] = value
            p.value = midi_to_pan(value) if self._mode == 0 else midi_to_param(p, value)
            self._last_touched = p
        return cb

    def handle_sysex(self, midi_bytes):
        b = midi_bytes
        if DEBUG:
            txt = " ".join("%02X" % x for x in b)
            self.show_message("02R SysEx : " + txt)
            self.log_message("02R SysEx : " + txt)
        if (len(b) == 8 and b[1] == 0x43 and (b[2] & 0xF0) == 0x10 and b[3] == 0x3D
                and b[4] == 0x1A and b[5] == 0x57):
            self._fine_adjust(b[6])
            return
        if len(b) != 9 or b[1] != 0x43 or (b[2] & 0xF0) != 0x10 or b[3] != 0x3D or b[4] != 0x19:
            return
        pressed = (b[7] == 0x01)

        addr = (b[5], b[6])
        if addr in (ARROW_LEFT, ARROW_RIGHT):
            if pressed:
                step = 1 if self._shift_held else NUM_STRIPS
                if self._shift_held:
                    self._shift_used = True
                self._shift(-step if addr == ARROW_LEFT else step)
            return

        if addr in EQ_BAND_BUTTONS:
            if pressed:
                target = EQ_BAND_BUTTONS[addr]
                if self._mode != target:
                    self._mode = target
                    self._rebind()
                self._status()
            return

        if addr == EQ_ON_BUTTON:
            if pressed:
                if self._mode != MODE_DEV:
                    self._mode = MODE_DEV
                    self._rebind()
                self._status()
            return

        if addr == SHIFT_ADDR:
            kind, n = "on", BTN_SHIFT
        else:
            kind, n = decode_button(b[5], b[6])
        if kind is None:
            return

        if kind == "sel":
            if pressed and n <= NUM_STRIPS:
                ch = n - 1
                now = time.time()
                if self._shift_held:
                    self._shift_used = True
                    self._toggle_solo(ch)
                elif self._last_sel[0] == ch and now - self._last_sel[1] < DOUBLE_PRESS:
                    self._toggle_arm(ch)
                    now = 0.0  # un triple appui ne re-declenche pas
                else:
                    self._select_strip(ch)
                self._last_sel = (ch, now)
            return

        if n <= NUM_STRIPS:
            ch = n - 1
            self._ignore_until[ch] = time.time() + IGNORE_WINDOW
            if pressed:
                self._console_on[ch] = not self._console_on[ch]
                track = self._track(ch)
                if track is not None:
                    track.mute = not self._console_on[ch]
            return

        if n == BTN_SHIFT:
            if pressed:
                self._shift_held = True
                self._shift_used = False
                if self._mode >= MODE_EQ:
                    self._page = 1
                    self._rebind()
                    self._status()
            else:
                self._shift_held = False
                if self._page:
                    self._page = 0
                    self._rebind()
                if not self._shift_used:
                    self._move_to(0)
                else:
                    self._status()
            return

        if not pressed:
            return

        if n == BTN_LEFT:
            self._shift_used = self._shift_held or self._shift_used
            self._shift(-1 if self._shift_held else -NUM_STRIPS)
        elif n == BTN_RIGHT:
            self._shift_used = self._shift_held or self._shift_used
            self._shift(1 if self._shift_held else NUM_STRIPS)
        elif n == BTN_MODE:
            if self._shift_held:
                self._shift_used = True
                self._follow = not self._follow
            else:
                self._mode = (self._mode + 1) % len(MODE_NAMES)
                self._rebind()
            self._status()

    def _select_strip(self, ch):
        track = self._track(ch)
        if track is None:
            return
        self.song().view.selected_track = track
        app_view = Live.Application.get_application().view
        try:
            app_view.show_view("Detail")
            app_view.show_view("Detail/DeviceChain")
        except Exception:
            pass
        dev = None
        try:
            for d in track.devices:
                name = d.name.upper()
                if any(k in name for k in EQ_NAME_KEYS):
                    dev = d
                    break
        except Exception:
            pass
        if dev is not None:
            self.song().view.select_device(dev)
            if DEBUG:
                self.log_message("02R PARAMS %s : %d parametres" % (dev.name, len(dev.parameters)))
                for i, prm in enumerate(dev.parameters):
                    self.log_message("02R PARAM %d | %s | %s" % (i, prm.name, prm.str_for_value(prm.value)))
        if self._mode != MODE_EQ:
            self._mode = MODE_EQ
        self.schedule_message(1, self._rebind)
        self.schedule_message(2, self._status)

    def _toggle_solo(self, ch):
        track = self._track(ch)
        if track is None:
            return
        track.solo = not track.solo
        self.show_message("02R : %s solo %s" % (track.name, "ON" if track.solo else "OFF"))

    def _toggle_arm(self, ch):
        track = self._track(ch)
        if track is None:
            return
        if not track.can_be_armed:
            self.show_message("02R : %s ne peut pas etre armee" % track.name)
            return
        track.arm = not track.arm
        self.show_message("02R : %s %s" % (track.name, "ARMEE" if track.arm else "desarmee"))

    def _fine_adjust(self, raw):
        p = self._last_touched
        if p is None:
            return
        delta = raw if raw < 64 else raw - 128
        try:
            if not p.is_enabled:
                return
            step = 1 if p.is_quantized else (p.max - p.min) / float(FINE_STEPS)
            p.value = max(p.min, min(p.max, p.value + delta * step))
            self.show_message("02R : %s = %s" % (p.name, p.str_for_value(p.value)))
        except Exception:
            self._last_touched = None  # reglage supprime entre-temps

    def _toggle_eq(self):
        dev = self._eq_device()
        if dev is None:
            self.show_message("02R : aucun MixHub/SSL sur la piste selectionnee")
            return
        params = list(dev.parameters)[1:]
        p = None
        # 1) recherche par nom : un parametre "EQ" + on/in/bypass/power
        for prm in params:
            n = prm.name.upper()
            if "EQ" in n and "INPUT" not in n and any(
                    k in n for k in ("ON", "IN", "BYP", "POWER", "ACTIVE", "ENABLE")):
                p = prm
                break
        if p is None:
            return  # pas de power EQ configure : le bouton ON ne fait rien
        if not p.is_enabled:
            return
        mid = (p.min + p.max) / 2.0
        p.value = p.max if p.value < mid else p.min
        self.show_message("02R : %s = %s" % (p.name, p.str_for_value(p.value)))

    # ---------- selection et devices ----------
    def _on_selected_track(self):
        self.schedule_message(1, self._after_selection)

    def _after_selection(self):
        self._watch_devices()
        if self._follow:
            track = self.song().view.selected_track
            tracks = self._tracks()
            if track in tracks:
                idx = tracks.index(track)
                if not (self._offset <= idx < self._offset + NUM_STRIPS):
                    self._move_to((idx // NUM_STRIPS) * NUM_STRIPS)
        if self._mode in (MODE_EQ, MODE_DEV):
            self._rebind()
            self._status()

    def _watch_devices(self):
        self._unwatch_devices()
        track = self.song().view.selected_track
        try:
            track.add_devices_listener(self._on_devices_changed)
            track.view.add_selected_device_listener(self._on_selected_device)
            self._dev_track = track
        except Exception:
            self._dev_track = None

    def _unwatch_devices(self):
        if self._dev_track is not None:
            try:
                if self._dev_track.devices_has_listener(self._on_devices_changed):
                    self._dev_track.remove_devices_listener(self._on_devices_changed)
                v = self._dev_track.view
                if v.selected_device_has_listener(self._on_selected_device):
                    v.remove_selected_device_listener(self._on_selected_device)
            except Exception:
                pass
        self._dev_track = None

    def _on_devices_changed(self):
        if self._mode in (MODE_EQ, MODE_DEV):
            self.schedule_message(1, self._rebind)

    def _on_selected_device(self):
        if self._mode == MODE_DEV:
            self.schedule_message(1, self._rebind)
            self.schedule_message(2, self._status)

    # ---------- Live -> console ----------
    def _make_vol_out(self, ch, param):
        def cb():
            v = vol_to_cc(param)
            if v != self._last_vol[ch]:
                self._last_vol[ch] = v
                self._send_midi((0xB0 | ch, CC_VOL, v))
        return cb

    def _make_knob_out(self, ch, param):
        is_pan = (self._mode == 0)
        def cb():
            v = pan_to_midi(param.value) if is_pan else param_to_midi(param)
            if v != self._last_knob[ch]:
                self._last_knob[ch] = v
                self._send_midi((0xB0 | ch, CC_KNOB, v))
        return cb

    def _unbind(self):
        for param, f in self._bound:
            try:
                if param.value_has_listener(f):
                    param.remove_value_listener(f)
            except Exception:
                pass
        self._bound = []

    def _on_tracks_changed(self):
        self.schedule_message(1, self._after_tracks_changed)

    def _after_tracks_changed(self):
        count = len(self._tracks())
        if self._offset >= count:
            self._offset = max(0, ((count - 1) // NUM_STRIPS) * NUM_STRIPS)
        self._rebind()

    def _rebind(self):
        self._unbind()
        self._last_vol = [None] * NUM_STRIPS
        self._last_knob = [None] * NUM_STRIPS
        for ch in range(NUM_STRIPS):
            track = self._track(ch)
            if track is None:
                self._send_midi((0xB0 | ch, CC_VOL, 0))
            else:
                vol = track.mixer_device.volume
                fv = self._make_vol_out(ch, vol)
                vol.add_value_listener(fv)
                self._bound.append((vol, fv))
                fv()
            kp = self._knob_param(ch)
            if kp is not None:
                fk = self._make_knob_out(ch, kp)
                kp.add_value_listener(fk)
                self._bound.append((kp, fk))
                fk()
            else:
                self._send_midi((0xB0 | ch, CC_KNOB, 64 if self._mode == 0 else 0))

    def disconnect(self):
        self._unbind()
        self._unwatch_devices()
        song = self.song()
        if song.tracks_has_listener(self._on_tracks_changed):
            song.remove_tracks_listener(self._on_tracks_changed)
        if song.view.selected_track_has_listener(self._on_selected_track):
            song.view.remove_selected_track_listener(self._on_selected_track)
        if self._udp is not None:
            try:
                self._udp.close()
            except Exception:
                pass
            self._udp = None
        ControlSurface.disconnect(self)


def create_instance(c_instance):
    return Yamaha02R(c_instance)
