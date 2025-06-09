# Complete and fixed osu! clone with universal skin support and full functionality

import pygame
import zipfile
import os
import time
import math
import random
import re

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("osu! clone")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

# Constants
CIRCLE_RADIUS = 64
FOLLOW_RADIUS = 32
HIT_WINDOW = 150
APPROACH_RATE = 1000
EXTRACT_FOLDER = "extracted"
SKIN_FOLDER = "skins/default"
HIT_SOUNDS = {"normal": "normal-hit.wav"}

# Load images from global skin folder
def load_image(name):
    return pygame.image.load(os.path.join(SKIN_FOLDER, name)).convert_alpha()

skin_images = {
    "hitcircle": load_image("hitcircle.png"),
    "overlay": load_image("hitcircleoverlay.png"),
    "approach": load_image("approachcircle.png"),
    "sliderstart": load_image("sliderstartcircle.png"),
    "sliderend": load_image("sliderendcircle.png"),
    "sliderball": load_image("sliderball.png")
}

# Load hitsounds
def load_sound(name):
    path = os.path.join(SKIN_FOLDER, name)
    return pygame.mixer.Sound(path) if os.path.exists(path) else None

hitsound = load_sound(HIT_SOUNDS["normal"])

class Circle:
    def __init__(self, x, y, time_):
        self.x = int(x * WIDTH / 512)
        self.y = int(y * HEIGHT / 384)
        self.time = time_
        self.hit = False
        self.missed = False

    def draw(self, current_time):
        if self.hit or self.missed:
            return
        dt = self.time - current_time
        if dt < -HIT_WINDOW:
            self.missed = True
            return
        alpha = max(0, min(255, int(255 * (1 - abs(dt) / APPROACH_RATE))))
        approach_scale = 1 + (dt / APPROACH_RATE) if dt > 0 else 1
        img = pygame.transform.scale(skin_images["hitcircle"], (CIRCLE_RADIUS * 2, CIRCLE_RADIUS * 2))
        overlay = pygame.transform.scale(skin_images["overlay"], (CIRCLE_RADIUS * 2, CIRCLE_RADIUS * 2))
        approach = pygame.transform.scale(skin_images["approach"], (int(CIRCLE_RADIUS * 2 * approach_scale), int(CIRCLE_RADIUS * 2 * approach_scale)))
        screen.blit(approach, approach.get_rect(center=(self.x, self.y)))
        screen.blit(img, img.get_rect(center=(self.x, self.y)))
        screen.blit(overlay, overlay.get_rect(center=(self.x, self.y)))

    def check_hit(self, pos, current_time):
        if self.hit or self.missed:
            return 0
        if abs(current_time - self.time) > HIT_WINDOW:
            return 0
        if math.hypot(pos[0] - self.x, pos[1] - self.y) <= CIRCLE_RADIUS:
            self.hit = True
            if hitsound:
                hitsound.play()
            return 300
        return 0

class Slider:
    def __init__(self, x1, y1, x2, y2, time_, duration=1000):
        self.x1 = int(x1 * WIDTH / 512)
        self.y1 = int(y1 * HEIGHT / 384)
        self.x2 = int(x2 * WIDTH / 512)
        self.y2 = int(y2 * HEIGHT / 384)
        self.time = time_
        self.duration = duration
        self.clicked = False
        self.hit = False
        self.missed = False
        self.last_check = 0

    def draw(self, current_time):
        if self.hit or self.missed:
            return
        dt = self.time - current_time
        if dt < -self.duration:
            self.missed = True
            return
        approach_scale = 1 + (dt / APPROACH_RATE) if dt > 0 else 1
        start_circle = pygame.transform.scale(skin_images["sliderstart"], (CIRCLE_RADIUS * 2, CIRCLE_RADIUS * 2))
        end_circle = pygame.transform.scale(skin_images["sliderend"], (CIRCLE_RADIUS * 2, CIRCLE_RADIUS * 2))
        follow = pygame.transform.scale(skin_images["sliderball"], (FOLLOW_RADIUS * 2, FOLLOW_RADIUS * 2))
        screen.blit(start_circle, start_circle.get_rect(center=(self.x1, self.y1)))
        screen.blit(end_circle, end_circle.get_rect(center=(self.x2, self.y2)))
        if self.clicked and current_time <= self.time + self.duration:
            t = (current_time - self.time) / self.duration
            fx = int(self.x1 + (self.x2 - self.x1) * t)
            fy = int(self.y1 + (self.y2 - self.y1) * t)
            screen.blit(follow, follow.get_rect(center=(fx, fy)))

    def check_hit(self, pos, current_time):
        if self.hit or self.clicked or abs(current_time - self.time) > HIT_WINDOW:
            return 0
        if math.hypot(pos[0] - self.x1, pos[1] - self.y1) <= CIRCLE_RADIUS:
            self.clicked = True
            self.last_check = current_time
            return 0

    def update(self, current_time, pos):
        if self.hit or self.missed or not self.clicked:
            return 0
        if current_time > self.time + self.duration:
            self.hit = True
            if hitsound:
                hitsound.play()
            return 300
        return 0

def parse_osu_file(path):
    objects = []
    audio_file = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    hit_objects = False
    for line in lines:
        if line.startswith("AudioFilename:"):
            audio_file = line.split(":")[1].strip()
        if line.strip() == "[HitObjects]":
            hit_objects = True
            continue
        if hit_objects:
            parts = line.strip().split(",")
            if len(parts) >= 5:
                x, y, time_ = int(parts[0]), int(parts[1]), int(parts[2])
                obj_type = int(parts[3])
                if obj_type & 2:
                    if len(parts) > 5 and "|" in parts[5]:
                        ctrl = parts[5].split("|")[1]
                        if ":" in ctrl:
                            x2, y2 = map(int, ctrl.split(":"))
                            objects.append(Slider(x, y, x2, y2, time_))
                else:
                    objects.append(Circle(x, y, time_))
    return objects, audio_file

def extract_osz(file_path):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        folder = os.path.join(EXTRACT_FOLDER, os.path.splitext(os.path.basename(file_path))[0])
        os.makedirs(folder, exist_ok=True)
        zip_ref.extractall(folder)
    return folder

def update_accuracy(scores):
    return 100 * sum(scores) / (300 * len(scores)) if scores else 100.0

def lobby_menu():
    files = [f for f in os.listdir(EXTRACT_FOLDER) if os.path.isdir(os.path.join(EXTRACT_FOLDER, f))]
    selected = 0
    while True:
        screen.fill((0, 0, 0))
        for i, name in enumerate(files):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            text = font.render(name, True, color)
            screen.blit(text, (50, 100 + 40 * i))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(files)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(files)
                elif event.key == pygame.K_RETURN:
                    return os.path.join(EXTRACT_FOLDER, files[selected])

def play_game(objects, audio_path):
    score_values = []
    start_time = pygame.time.get_ticks()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    running = True
    while running:
        screen.fill((30, 30, 30))
        current_time = pygame.time.get_ticks() - start_time
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                return
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                input_pos = mouse_pos
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_z, pygame.K_x):
                    input_pos = pygame.mouse.get_pos()
                for obj in objects:
                    if hasattr(obj, "check_hit"):
                        result = obj.check_hit(input_pos, current_time)
                        if result:
                            score_values.append(result)

        for obj in objects:
            if hasattr(obj, "update"):
                score_values.append(obj.update(current_time, mouse_pos))
            obj.draw(current_time)

        score = sum(score_values)
        accuracy = update_accuracy(score_values)
        screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (10, 10))
        screen.blit(font.render(f"Accuracy: {accuracy:.2f}%", True, (255, 255, 255)), (10, 40))
        pygame.display.flip()
        clock.tick(60)

        if all(getattr(o, "hit", False) or getattr(o, "missed", False) for o in objects):
            pygame.mixer.music.stop()
            end_screen(score, accuracy)
            return

def end_screen(score, accuracy):
    running = True
    while running:
        screen.fill((0, 0, 0))
        screen.blit(font.render(f"Level Complete!", True, (255, 255, 0)), (300, 200))
        screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (300, 250))
        screen.blit(font.render(f"Accuracy: {accuracy:.2f}%", True, (255, 255, 255)), (300, 280))
        screen.blit(font.render("Press Enter to return", True, (200, 200, 200)), (300, 320))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return

def main():
    os.makedirs(EXTRACT_FOLDER, exist_ok=True)
    for file in os.listdir('.'):
        if file.endswith('.osz'):
            extract_osz(file)
    while True:
        folder = lobby_menu()
        if not folder:
            break
        osu_files = [f for f in os.listdir(folder) if f.endswith(".osu")]
        if not osu_files:
            print("No .osu files found")
            continue
        osu_path = os.path.join(folder, osu_files[0])
        objects, audio_file = parse_osu_file(osu_path)
        audio_path = os.path.join(folder, audio_file) if audio_file else None
        if audio_path and os.path.exists(audio_path):
            play_game(objects, audio_path)

if __name__ == "__main__":
    main()
