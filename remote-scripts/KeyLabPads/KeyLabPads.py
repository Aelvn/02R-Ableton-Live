# -*- coding: utf-8 -*-
# KeyLabPads - Remote Script pour Ableton Live 12
# Ajoute des fonctions aux 16 pads du KeyLab Essential mk3
# (template User du MIDI Control Center, pads en notes Gate sur le canal 16)

import Live
from _Framework.ControlSurface import ControlSurface

# ---------------------------------------------------------------
# REGLAGES
# ---------------------------------------------------------------
PAD_CHANNEL = 15   # canal 16 (Ableton compte les canaux de 0 a 15)
BASE_NOTE = 36     # note du pad 1 de la banque A (36 = C1 dans Ableton)
# Si le pad A1 affiche "note XX non assignee" dans la barre d'etat
# d'Ableton, remplace 36 par ce numero XX.
# ---------------------------------------------------------------


class KeyLabPads(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._actions = [
            # ---- Banque A : Enregistrement ----
            ("Enregistrement", self._toggle_record),
            ("Capture MIDI", self._capture_midi),
            ("Metronome", self._toggle_metronome),
            ("Boucle", self._toggle_loop),
            ("Annuler", self._undo),
            ("Retablir", self._redo),
            ("Overdub MIDI", self._toggle_overdub),
            ("Tap tempo", self._tap_tempo),
            # ---- Banque B : Navigation et composition ----
            ("Marqueur", self._set_or_delete_marker),
            ("Marqueur precedent", self._prev_marker),
            ("Marqueur suivant", self._next_marker),
            ("Armer la piste", self._arm_selected_track),
            ("Piste precedente", self._prev_track),
            ("Piste suivante", self._next_track),
            ("Retour au debut", self._go_to_start),
            ("Reactiver l'automation", self._reenable_automation),
        ]
        self.log_message("KeyLabPads : script charge")
        self.show_message("KeyLabPads prêt")

    def disconnect(self):
        self.log_message("KeyLabPads : script decharge")
        ControlSurface.disconnect(self)

    # -----------------------------------------------------------
    # MIDI
    # -----------------------------------------------------------
    def build_midi_map(self, midi_map_handle):
        ControlSurface.build_midi_map(self, midi_map_handle)
        script_handle = self._c_instance.handle()
        # Le canal 16 est reserve aux pads : on recupere toutes ses notes
        for note in range(128):
            Live.MidiMap.forward_midi_note(
                script_handle, midi_map_handle, PAD_CHANNEL, note)

    def receive_midi(self, midi_bytes):
        if len(midi_bytes) == 3:
            status, note, velocity = midi_bytes
            msg_type = status & 0xF0
            channel = status & 0x0F
            if channel == PAD_CHANNEL and msg_type in (0x80, 0x90):
                if msg_type == 0x90 and velocity > 0:
                    self._on_pad(note)
                return
        ControlSurface.receive_midi(self, midi_bytes)

    def _on_pad(self, note):
        index = note - BASE_NOTE
        if 0 <= index < len(self._actions):
            name, action = self._actions[index]
            self.log_message("KeyLabPads : note %d -> %s" % (note, name))
            try:
                action()
            except Exception as e:
                self.log_message("KeyLabPads : erreur sur %s : %s" % (name, e))
                self.show_message("KeyLabPads : erreur sur %s" % name)
        else:
            self.log_message("KeyLabPads : note %d non assignee" % note)
            self.show_message("KeyLabPads : note %d non assignée" % note)

    # -----------------------------------------------------------
    # OUTILS
    # -----------------------------------------------------------
    def _status(self, label, state):
        self.show_message("%s : %s" % (label, "ON" if state else "OFF"))

    # -----------------------------------------------------------
    # BANQUE A : ENREGISTREMENT
    # -----------------------------------------------------------
    def _toggle_record(self):
        song = self.song()
        song.record_mode = not song.record_mode
        self._status("Enregistrement", song.record_mode)

    def _capture_midi(self):
        song = self.song()
        if song.can_capture_midi:
            song.capture_midi()
            self.show_message("Capture MIDI effectuée")
        else:
            self.show_message("Rien à capturer")

    def _toggle_metronome(self):
        song = self.song()
        song.metronome = not song.metronome
        self._status("Métronome", song.metronome)

    def _toggle_loop(self):
        song = self.song()
        song.loop = not song.loop
        self._status("Boucle", song.loop)

    def _undo(self):
        song = self.song()
        if song.can_undo:
            song.undo()
            self.show_message("Annuler")

    def _redo(self):
        song = self.song()
        if song.can_redo:
            song.redo()
            self.show_message("Rétablir")

    def _toggle_overdub(self):
        song = self.song()
        song.arrangement_overdub = not song.arrangement_overdub
        self._status("Overdub MIDI", song.arrangement_overdub)

    def _tap_tempo(self):
        song = self.song()
        song.tap_tempo()
        self.show_message("Tempo : %.1f BPM" % song.tempo)

    # -----------------------------------------------------------
    # BANQUE B : NAVIGATION ET COMPOSITION
    # -----------------------------------------------------------
    def _set_or_delete_marker(self):
        self.song().set_or_delete_cue()
        self.show_message("Marqueur ajouté / supprimé")

    def _prev_marker(self):
        song = self.song()
        if song.can_jump_to_prev_cue:
            song.jump_to_prev_cue()
            self.show_message("Marqueur précédent")

    def _next_marker(self):
        song = self.song()
        if song.can_jump_to_next_cue:
            song.jump_to_next_cue()
            self.show_message("Marqueur suivant")

    def _arm_selected_track(self):
        track = self.song().view.selected_track
        if track.can_be_armed:
            track.arm = not track.arm
            self._status("Armement %s" % track.name, track.arm)
        else:
            self.show_message("Cette piste ne peut pas être armée")

    def _select_track(self, step):
        song = self.song()
        tracks = list(song.visible_tracks)
        if not tracks:
            return
        current = song.view.selected_track
        if current in tracks:
            index = tracks.index(current) + step
        else:
            index = 0
        index = max(0, min(len(tracks) - 1, index))
        song.view.selected_track = tracks[index]
        self.show_message("Piste : %s" % tracks[index].name)

    def _prev_track(self):
        self._select_track(-1)

    def _next_track(self):
        self._select_track(1)

    def _go_to_start(self):
        self.song().current_song_time = 0.0
        self.show_message("Retour au début")

    def _reenable_automation(self):
        song = self.song()
        if song.re_enable_automation_enabled:
            song.re_enable_automation()
            self.show_message("Automation réactivée")
        else:
            self.show_message("Automation déjà active")
