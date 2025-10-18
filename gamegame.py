import pyglet 
from pyglet.window import key
import math

snd = pyglet.media.load('music/potential_intogame_track.wav', streaming=False)
player = pyglet.media.Player()
player.loop = True
player.queue(snd)
player.play()


# set resource path to imgs
pyglet.resource.path = ['img', 'img/bg']
pyglet.resource.reindex()


# scene management
current_scene = None

def set_scene(scene):
    global current_scene
    if current_scene is not None:
        current_scene.on_exit()
    current_scene = scene
    current_scene.on_enter()

class Scene:
    def on_enter(self): pass
    def on_exit(self): pass
    def on_draw(self): pass
    def on_key_press(self, symbol, modifiers): pass

class DialogueManager:
    def __init__(self):
        self.active = False
        self.dialogues = []
        self.current_index = 0
        self.choice = None # for if change player character

    def start(self, dialogue_list, choice=None):
        self.dialogues = dialogue_list
        self.current_index = 0
        self.active = True
        self.choice = choice # (question, {key: (label, outcome)})

    def next(self):
        if self.active:
            self.current_index += 1
            if self.current_index >= len(self.dialogues) and not self.choice:
                self.end()

    def end(self):
        self.active = False
        self.dialogues = []
        self.current_index = 0

    def get_current_line(self):
        if self.active and self.dialogues and self.current_index < len(self.dialogues):
            return self.dialogues[self.current_index]  # returns (speaker, text)
        return None

    def is_active(self):
        return self.active


class MainMenu(Scene):
    tile_map = [
    ["grass", "grass", "road", "grass"],
    ["grass", "road", "road", "grass"],
    ["grass", "grass", "grass_and_shrooms_b", "grass"]
]

    def __init__(self, window):
        self.window = window
        self.player = player
        self.bg_image = pyglet.resource.image('frame_bb.png')# bg image
        tile_images = {
            "grass": pyglet.resource.image("grass.png"),
            "road": pyglet.resource.image("road.png"),
            "grass_and_shrooms_b": pyglet.resource.image("grass_and_shrooms_b.png")
        }


        self.volume = self.player.volume

    def on_enter(self):
        self.window.controls_enabled = False

    def on_exit(self):
        self.window.controls_enabled = True

    def on_draw(self):
        self.window.clear()
        x = (self.window.width - self.bg_image.width) // 2
        y = (self.window.height - self.bg_image.height) // 2
        self.bg_image.blit(x, y)

                # draw volume bar (simple rectangle)
        bar_width = 300
        bar_height = 20
        bar_x = self.window.width // 2 - bar_width // 2
        bar_y = self.window.height // 2 - 180

        # background bar (gray)
        pyglet.shapes.Rectangle(bar_x, bar_y, bar_width, bar_height, color=(100, 100, 100)).draw()

        # filled portion (yellow)
        fill_width = int(bar_width * self.volume)
        pyglet.shapes.Rectangle(bar_x, bar_y, fill_width, bar_height, color=(255, 255, 0)).draw()


        labels = [
            ("Main Menu", 36, self.window.height // 2 + 100),
            ("Press ENTER to Start Game", 18, self.window.height // 2),
            ("Press ESCAPE to Close Game", 18, self.window.height // 2 - 50),
            (f"Music Volume: {int(self.volume * 100)}%", 18, self.window.height // 2 - 100),
            ("Use LEFT / RIGHT to adjust volume", 14, self.window.height // 2 - 130)
        ]

        for text, size, y_pos in labels:
            pyglet.text.Label(
                text, font_size=size,
                x=self.window.width // 2,
                y=y_pos,
                anchor_x="center"
            ).draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ENTER:
            set_scene(GameLevel(self.window)) # switch to game
        elif symbol == key.ESCAPE:
            pyglet.app.exit() # exit game
        elif symbol == key.LEFT:
            self.volume = max(0.0, self.volume - 0.1)  # decrease
            self.player.volume = self.volume
        elif symbol == key.RIGHT:
            self.volume = min(1.0, self.volume + 0.1)  # increase
            self.player.volume = self.volume

class GameLevel(Scene):
    def __init__(self, window):
        self.window = window
        self.dialogue_manager = DialogueManager()
        self.dialogue_box_width = 1300
        self.dialogue_box_height = 200


        # dialogue box image
        self.textbox_img = pyglet.resource.image('textbox.png')
        self.textbox_img.anchor_x = 0
        self.textbox_img.anchor_y = 0

        # portraits
        self.ezra_portrait = pyglet.resource.image('ez/ezratalk.png')
        self.jan_portrait = pyglet.resource.image('jan/jantalk_1.png')

        # tutorial message setup
        self.show_tutorial = True
        self.tutorial_text = "Move with the arrow keys or 'A' 'W' 'S' 'D' \n\nInteract with characters or items with 'E'!"
        
        # npc dialogues
        self.npc_dialogues = {
            "shroom": [
                ("DANCING SHROOM", "Do not go into the forest! It is too dangerous!")
            ],
            "ezra": [
                ("EZRA", "You finally made it, huh? I've been waiting for you."),
                ("JAN", "Are you still mad at me?"),
                ("EZRA", "...a little. You lost my favourite hat!"),
                ("JAN", "I'm sorry, do you want me to find it?"),
                ("EZRA", "I know where it is. It's in the forest."),
                ("EZRA", "But it's dangerous there.")
            ]
        }

        # choice definition
        self.ezra_choice = (
            "OFFER TO GO IN THE FOREST INSTEAD OF EZRA?",
            {
                key.Y: (" Yes", "yes_outcome"),
                key.N: (" No", "no_outcome"),
            }
        )

        # check if first convo with ezra
        self.ezra_first_talked = False

        # choice forest
        self.forest_choice = (
            "WALK INTO FOREST?",
            {
                key.Y: (" Yes", "forest_yes"),
                key.N: (" No", "forest_no"),
            }
        )




    def on_enter(self):
        # disable player controls until tutorial is closed
        self.window.controls_enabled = False

    def on_exit(self):
        self.dialogue_manager.end()
        self.show_tutorial = False

    # interaction helpers
    def check_proximity(self, target, radius=200):
        dx = self.window.sprite.x - target.x
        dy = self.window.sprite.y - target.y 
        dist = math.hypot(dx, dy)
        return dist < radius
    
    def start_dialogue(self, dialogue):
        self.dialogue_manager.start(dialogue)
        self.window.controls_enabled = False

    def on_draw(self):
        self.window.clear()
        # draw map first (background)
        draw_tilemap(self.tile_map)
        self.window.sprite.draw()
        self.window.npc.draw()
        self.window.ezra.draw()

        # draw tutorial box if it's active
        if self.show_tutorial:
            self.draw_tutorial()
        elif self.dialogue_manager.is_active() or self.dialogue_manager.choice:
            self.draw_dialogue_box()

    def draw_tutorial(self):
        center_x = (self.window.width - self.dialogue_box_width) // 2
        center_y = (self.window.height - self.dialogue_box_height) // 2

        self.textbox_img.blit(
            center_x, center_y,
            width=self.dialogue_box_width,
            height=self.dialogue_box_height * 2.1
        )

        # tutorial text
        pyglet.text.Label(
            self.tutorial_text,
            font_size = 38,
            x=center_x + 40,
            y=center_y + self.dialogue_box_height - 20,
            width=self.dialogue_box_width - 30,
            multiline=True,
            anchor_x="left",
            anchor_y="bottom",
            color=(255, 255, 255, 255)
        ).draw()

        # press E prompt
        pyglet.text.Label(
            "Press 'E' to continue",
            font_size=25,
            x=center_x + self.dialogue_box_width // 2,
            y=center_y + 15,
            anchor_x="center",
            anchor_y="bottom",
            color=(200, 200, 200, 255)
        ).draw()

    # npc dialogue box if in dialogue mode
    def draw_dialogue_box(self):
        line = self.dialogue_manager.get_current_line()

        # portrait settings
        portrait_height = self.dialogue_box_height + 75
        portrait_margin = 40
        portrait_width = portrait_height
        box_width = self.window.width - portrait_width - portrait_margin * 2
        portrait_width = portrait_height  # square portraits
        box_height = self.dialogue_box_height

        # draw dialogue box
        self.textbox_img.blit(
            portrait_margin, 0,
            width=box_width,
            height=box_height
        )

        # If in choice mode, draw choices and return
        if self.dialogue_manager.choice and line is None:
            question, options = self.dialogue_manager.choice

            # draw question
            pyglet.text.Label(
                question,
                font_size=28,
                x=portrait_margin + 20, y=box_height - 40,
                anchor_x="left", anchor_y="top",
                color=(255, 255, 255, 255)
            ).draw()

            # draw y/n options
            y_offset = box_height - 80
            for k, (label, _) in options.items():
                key_name = pyglet.window.key.symbol_string(k)
                pyglet.text.Label(
                    f"Press {pyglet.window.key.symbol_string(k)}: {label}",
                    font_size=22,
                    x=portrait_margin + 40, y=y_offset,
                    anchor_x="left", anchor_y="top",
                    color=(200, 200, 200, 255)
                ).draw()
                y_offset -= 36
            return 
        
        # Otherwise draw the current line (if any)
        if not line:
            return

        # otherwise, draw normal dialogue
        speaker, text = line

        # portrait position
        portrait_x = portrait_margin + box_width + portrait_margin // 2
        portrait_y = 30
        if speaker == "EZRA":
            scale = portrait_height / self.ezra_portrait.height
            self.ezra_portrait.blit(
                portrait_x, portrait_y,
                width=int(self.ezra_portrait.width * scale),
                height=int(self.ezra_portrait.height * scale)
            )
        elif speaker == "JAN":
            scale = portrait_height / self.jan_portrait.height
            self.jan_portrait.blit(
                portrait_x, portrait_y,
                width=int(self.jan_portrait.width * scale),
                height=int(self.jan_portrait.height * scale)
            )

        # draw speaker name
        text_x = portrait_margin + 20
        text_width = box_width - 40
        pyglet.text.Label(
            f"{speaker}:", font_size=28,
            x=text_x, y=box_height - 40,
            anchor_x="left", anchor_y="top",
            color=(255, 255, 100, 255)
        ).draw()

        # draw dialogue text
        pyglet.text.Label(
            text,
            font_size=28,
            x=text_x,
            y=box_height - 80,
            width=text_width,
            multiline=True,
            anchor_x="left",
            anchor_y="top",
            color=(255, 255, 255, 255)
    ).draw()


    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE: # pause to main menu
            set_scene(MainMenu(self.window))
            return

        # if choice is active (we are waiting for y/n), handle it first
        if self.dialogue_manager.choice and not self.dialogue_manager.get_current_line():
            question, options = self.dialogue_manager.choice
            if symbol in options:
                _, outcome = options[symbol]
                # handle outcomes
                if outcome == "yes_outcome":
                    self.dialogue_manager.start([
                        ("JAN", "I can go in myself."),
                        ("EZRA", "Well, if you're sure..."),
                        ("EZRA", "Just tell me when you're going. Okay?")
                    ])
                elif outcome == "no_outcome":
                    self.dialogue_manager.start([
                        ("EZRA", "I'll go, you stay here."),
                        ("JAN", "Are you sure?"),
                        ("EZRA", "Yes, I can handle it. I'll talk to you before I go in.")
                    ])
                    if hasattr(self.window, "swap_control_to_ezra"):
                        self.window.swap_control_to_ezra()
                elif outcome == "forest_yes":
                    set_scene(ForestLevel(self.window, self.window.current_player))
                elif outcome == "forest_no":
                    self.dialogue_manager.start([
                        ("EZRA", "Maybe it's not the right time."),
                        ("JAN", "I know, there's no hurry."),
                    ])
            return

        # dialogue
        if symbol == key.E:
            # close tutorial with e if visible
            if self.show_tutorial:
                self.show_tutorial = False
                self.window.controls_enabled = True
                return

            # if currently in a dialogue, step it
            if self.dialogue_manager.is_active():
                self.dialogue_manager.next()
                # if dialogue ended, re-enable controls
                if not self.dialogue_manager.is_active():
                    self.window.controls_enabled = True
                return

            # otherwise attempt interactions (check proximity to npcs)
            near_npc = self.check_proximity(self.window.npc)
            near_ezra = self.check_proximity(self.window.ezra)
            print(f"Jan: ({self.window.sprite.x}, {self.window.sprite.y}), Mushroom: ({self.window.npc.x}, {self.window.npc.y}), Distance: {math.hypot(self.window.sprite.x - self.window.npc.x, self.window.sprite.y - self.window.npc.y)}")

            if near_npc:
                # mushroom dialogue
                self.start_dialogue(self.npc_dialogues["shroom"])
                return
            if near_ezra:
                if not self.ezra_first_talked:
                    # 1 talk Ezra
                    self.dialogue_manager.start(self.npc_dialogues["ezra"], self.ezra_choice)
                    self.ezra_first_talked = True
                else:
                    # 2 talk and whos the player
                    if self.window.current_player == "jan":  # jan
                        self.dialogue_manager.start([
                            ("JAN", "I'm ready to go in."),
                            ("EZRA", "Okay, you better take this, it's not safe to go in alone.")
                        ], self.forest_choice)
                    else:  # ezra 
                        self.dialogue_manager.start([
                            ("EZRA", "I'm going in now."),
                            ("JAN", "Don't die!"),
                            ("EZRA", "...")
                        ], self.forest_choice)
                self.window.controls_enabled = False
                return



class GameWindow(pyglet.window.Window):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.set_caption("JanJan Game")

        # window icon(might change later)
        icon = pyglet.resource.image('icon.png')
        self.set_icon(icon)

        # load animations
        # right/up
        runR_sheet = pyglet.resource.image('jan/janrunR_b.png')
        runR_frame_width = runR_sheet.width // 4
        runR_frame_height = runR_sheet.height
        runR_frames = pyglet.image.ImageGrid(runR_sheet, 1, 4)
        self.janrun_right_up = pyglet.image.Animation.from_image_sequence(
            runR_frames, 0.15, loop=True
        )

        # left/down
        runL_sheet = pyglet.resource.image('jan/janrunL_b.png')
        runL_frame_width = runL_sheet.width // 4
        runL_frame_height = runL_sheet.height
        runL_frames = pyglet.image.ImageGrid(runL_sheet, 1, 4)
        self.janrun_left_down = pyglet.image.Animation.from_image_sequence(
            runL_frames, 0.15, loop=True
        )

        # idle animation
        idle_sheet = pyglet.resource.image('jan/janjanidle_blink.png')
        idle_frame_width = idle_sheet.width // 4
        idle_frame_height = idle_sheet.height
        idle_frames = pyglet.image.ImageGrid(idle_sheet, 1, 4)
        self.janrun_idle = pyglet.image.Animation.from_image_sequence(idle_frames, 0.3, loop=True)

        # set anchor points for all animations
        for frame in self.janrun_idle.frames:
            frame.image.anchor_x = idle_frame_width // 2
            frame.image.anchor_y = idle_frame_height // 2

        for frame in self.janrun_right_up.frames:
            frame.image.anchor_x = runR_frame_width // 2
            frame.image.anchor_y = runR_frame_height // 2

        for frame in self.janrun_left_down.frames:
            frame.image.anchor_x = runL_frame_width // 2
            frame.image.anchor_y = runL_frame_height // 2

        # center anchors for other animations
        for anim in (self.janrun_left_down, self.janrun_right_up, self.janrun_idle):
            for frame in anim.frames:
                frame.image.anchor_x = frame.image.width // 2
                frame.image.anchor_y = frame.image.height // 2


        self.sprite = pyglet.sprite.Sprite(self.janrun_right_up, x=200, y=200)
        self.sprite.scale = 1.0
        self.current_player = "jan"
        
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)

        self.current_anim = "run_right_up"

        # npc animation
        try:
            npc_sheet = pyglet.resource.image('messangerMushroom_B.png') 
        except pyglet.resource.ResourceNotFoundException:
            raise SystemExit("Could not find messangerMushroom.png")
        
        try:
            ezra_sheet = pyglet.resource.image('ez/ezraIdle_b.png') 
        except pyglet.resource.ResourceNotFoundException:
            raise SystemExit("Could not find ezraIdle_b.png")

        frame_width = npc_sheet.width // 4
        frame_height = npc_sheet.height // 1
        npc_frames = pyglet.image.ImageGrid(npc_sheet, 1, 4)
        npc_animation = pyglet.image.Animation.from_image_sequence(npc_frames, 0.4, loop=True)

        frame_width = ezra_sheet.width // 4
        frame_height = ezra_sheet.height // 1
        ezra_frames = pyglet.image.ImageGrid(ezra_sheet, 1, 4)
        ezra_animation = pyglet.image.Animation.from_image_sequence(ezra_frames, 0.3, loop=True)

        # anchor
        for frame in npc_animation.frames:
            frame.image.anchor_x = frame_width // 2
            frame.image.anchor_y = frame_height // 2

        for frame in ezra_animation.frames:
            frame.image.anchor_x = frame_width // 2
            frame.image.anchor_y = frame_height // 2

        # npc
        self.npc = pyglet.sprite.Sprite(npc_animation, x=1000, y=600)
        self.npc.scale = 1.0
        
        # ezra
        self.ezra = pyglet.sprite.Sprite(ezra_animation, x=1500, y=600)
        self.ezra.scale = 1.0 # bc the small spritelooked too lowquality

        self.controls_enabled = True

    def swap_control_to_ezra(self):
        # Replace controllable sprite with Ezra
        ezra_runR_sheet = pyglet.resource.image('ez/ezrarunR_b.png')
        ezra_runL_sheet = pyglet.resource.image('ez/ezrarunL_b.png')
        ezra_idle_sheet = pyglet.resource.image('ez/ezraIdle_b.png')

        runR_frames = pyglet.image.ImageGrid(ezra_runR_sheet, 1, 4)
        runL_frames = pyglet.image.ImageGrid(ezra_runL_sheet, 1, 4)
        idle_frames = pyglet.image.ImageGrid(ezra_idle_sheet, 1, 4)

        # create animations
        self.ezra_run_right = pyglet.image.Animation.from_image_sequence(runR_frames, 0.15, loop=True)
        self.ezra_run_left  = pyglet.image.Animation.from_image_sequence(runL_frames, 0.15, loop=True)
        self.ezra_idle      = pyglet.image.Animation.from_image_sequence(idle_frames, 0.3, loop=True)

        # anchor all frames for ezra animations
        for anim in (self.ezra_run_right, self.ezra_run_left, self.ezra_idle):
            for frame in anim.frames:
                frame.image.anchor_x = frame.image.width // 2
                frame.image.anchor_y = frame.image.height // 2

        # swap playable sprite
        self.sprite.image = self.ezra_idle
        self.current_player = "ezra"

        # replace ezra npc with jan
        jan_idle = pyglet.resource.image('jan/janjanidle_blink.png')
        jan_frames = pyglet.image.ImageGrid(jan_idle, 1, 4)
        jan_anim = pyglet.image.Animation.from_image_sequence(jan_frames, 0.3, loop=True)
        for frame in jan_anim.frames:
            frame.image.anchor_x = frame.image.width // 2
            frame.image.anchor_y = frame.image.height // 2

        self.ezra.image = jan_anim


    def on_draw(self):
        self.clear()
        if current_scene:
            current_scene.on_draw()

    def on_key_press(self, symbol, modifiers):
        if current_scene:
            current_scene.on_key_press(symbol, modifiers)

    def update(self, dt):
        if not self.controls_enabled:
            return

        moving = False
        new_anim = None
        
        if self.keys[pyglet.window.key.LEFT] or self.keys[pyglet.window.key.A]:
            self.sprite.x -= 300 * dt
            if not new_anim:
                new_anim = "run_left"
            moving = True
        elif self.keys[pyglet.window.key.RIGHT] or self.keys[pyglet.window.key.D]:
            self.sprite.x += 300 * dt
            if not new_anim:
                new_anim = "run_right"
            moving = True

        if self.keys[pyglet.window.key.UP] or self.keys[pyglet.window.key.W]:
            self.sprite.y += 300 * dt
            if not new_anim:
                new_anim = "run_right"
            moving = True
        elif self.keys[pyglet.window.key.DOWN] or self.keys[pyglet.window.key.S]:
            self.sprite.y -= 300 * dt
            if not new_anim:
                new_anim = "run_left"
            moving = True

        if not moving:
            new_anim = "idle"

        # change animation if state changes
        if self.current_player == "jan":
            left_anim = self.janrun_left_down
            right_anim = self.janrun_right_up
            idle_anim = self.janrun_idle
        else:  # ezra
            left_anim = getattr(self, "ezra_run_left", self.janrun_left_down)
            right_anim = getattr(self, "ezra_run_right", self.janrun_right_up)
            idle_anim = getattr(self, "ezra_idle", self.janrun_idle)

        # change animation if state changes
        if new_anim != self.current_anim:
            if new_anim == "run_left":
                self.sprite.image = left_anim
            elif new_anim == "run_right":
                self.sprite.image = right_anim
            elif new_anim == "idle":
                self.sprite.image = idle_anim
            self.current_anim = new_anim

            # change animation if state changes
        if new_anim != self.current_anim:
            if new_anim == "run_left":
                self.sprite.image = left_anim
            elif new_anim == "run_right":
                self.sprite.image = right_anim
            elif new_anim == "idle":
                self.sprite.image = idle_anim
            self.current_anim = new_anim

        # --- prevent walking off screen ---
        half_width = self.sprite.width // 2
        half_height = self.sprite.height // 2

        # clamp inside window bounds
        if self.sprite.x < half_width:
            self.sprite.x = half_width
        if self.sprite.x > self.width - half_width:
            self.sprite.x = self.width - half_width
        if self.sprite.y < half_height:
            self.sprite.y = half_height
        if self.sprite.y > self.height - half_height:
            self.sprite.y = self.height - half_height



class ForestLevel(GameLevel):
    def __init__(self, window, player_character="jan"):
        super().__init__(window)
        self.player_character = player_character

        # clear scene from characters from last scene
        self.window.npc.visible = False
        self.window.ezra.visible = False

        # no tutorial and dialogue 
        self.show_tutorial = False
        self.npc_dialogues = {}

        # maybe could add new dialogues or items here if you want

    def on_enter(self):
    # set the correct player sprite
        if self.player_character == "ezra":
            if self.window.current_player != "ezra":
                self.window.swap_control_to_ezra()
        else:  # jan
            if self.window.current_player != "jan":
                # revert to jan (use jan’s idle animation)
                self.window.sprite.image = self.window.janrun_idle
                self.window.current_player = "jan"

        # hide NPCs (forest is empty for now)
        self.window.npc.visible = False
        self.window.ezra.visible = False

        self.window.controls_enabled = True
        self.dialogue_manager.end()



# create the game window
window = GameWindow(1800, 1600)
set_scene(MainMenu(window))  # start with the main menu
pyglet.clock.schedule_interval(window.update, 1/60.0)
pyglet.app.run()
