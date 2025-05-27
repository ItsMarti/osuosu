import pygame
import zipfile
import os
import math

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("osu! clone")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

EXTRACT_FOLDER = "extracted"
SKIN_FOLDER = "skins/default"

def load_skin(filename):
    return pygame.image.load(os.path.join(SKIN_FOLDER, filename)).convert_alpha()

hitcircle_img = load_skin("hitcircle.png")
hitcircleoverlay_img = load_skin("hitcircleoverlay.png")
sliderstartcircle_img = load_skin("sliderstartcircle.png")
sliderendcircle_img = load_skin("sliderendcircle.png")
sliderbody_img = load_skin("sliderbody.png")
sliderball_img = load_skin("sliderball.png")

class Circle:
    def __init__(self, x, y, appear_time):
        self.x = int(x * WIDTH / 512)
        self.y = int(y * HEIGHT / 384)
        self.appear_time = appear_time
        self.hit = False
        self.missed = False
        self.radius = 64
        self.fade_in_time = 500  # fade-in duration ms
        self.hit_window = 150    # ms hit window before/after

    def draw(self, current_time):
        # disappear if hit or missed and time after window passed
        if self.hit or (self.missed and current_time > self.appear_time + self.hit_window):
            return

        # skip drawing before fade-in
        if current_time < self.appear_time - self.fade_in_time:
            return

        # fade in alpha
        alpha = min(255, max(0, int(255 * (current_time - (self.appear_time - self.fade_in_time)) / self.fade_in_time)))
        surf = hitcircle_img.copy()
        surf.set_alpha(alpha)
        rect = surf.get_rect(center=(self.x, self.y))
        screen.blit(surf, rect)

        overlay = hitcircleoverlay_img.copy()
        overlay.set_alpha(alpha)
        screen.blit(overlay, rect)

        # Approach circle
        time_until_hit = self.appear_time - current_time
        if time_until_hit > 0:
            approach_radius = int(self.radius + 2 * self.radius * (time_until_hit / 1000))
            pygame.draw.circle(screen, (0, 255, 0), (self.x, self.y), approach_radius, 2)

    def check_hit(self, pos, current_time):
        if self.hit or self.missed:
            return 0
        # If outside hit window, mark missed
        if abs(current_time - self.appear_time) > self.hit_window:
            if current_time > self.appear_time + self.hit_window:
                self.missed = True
            return 0

        dx, dy = pos[0] - self.x, pos[1] - self.y
        if math.hypot(dx, dy) <= self.radius:
            self.hit = True
            return 300
        return 0

class Slider:
    def __init__(self, x1, y1, x2, y2, appear_time, repeats=1, duration=1000):
        self.x1 = int(x1 * WIDTH / 512)
        self.y1 = int(y1 * HEIGHT / 384)
        self.x2 = int(x2 * WIDTH / 512)
        self.y2 = int(y2 * HEIGHT / 384)
        self.appear_time = appear_time
        self.repeats = repeats
        self.duration = duration
        self.hit = False
        self.clicked = False
        self.missed = False
        self.radius = 64
        self.follow_radius = 32
        self.last_check_time = 0
        self.fade_in_time = 500
        self.hit_window = 150

    def draw(self, current_time):
        if self.hit or current_time < self.appear_time - self.fade_in_time:
            return

        alpha = min(255, max(0, int(255 * (current_time - (self.appear_time - self.fade_in_time)) / self.fade_in_time)))

        # Draw slider track (sliderbody.png repeated along line)
        track_surf = sliderbody_img.copy()
        track_surf.set_alpha(alpha)
        for i in range(0, 101, 5):
            t = i / 100
            x = int(self.x1 + (self.x2 - self.x1) * t)
            y = int(self.y1 + (self.y2 - self.y1) * t)
            rect = track_surf.get_rect(center=(x, y))
            screen.blit(track_surf, rect)

        # Start and end circles
        start_surf = sliderstartcircle_img.copy()
        start_surf.set_alpha(alpha)
        screen.blit(start_surf, start_surf.get_rect(center=(self.x1, self.y1)))

        end_surf = sliderendcircle_img.copy()
        end_surf.set_alpha(alpha)
        screen.blit(end_surf, end_surf.get_rect(center=(self.x2, self.y2)))

        # Slider ball moving along track during active duration
        if self.appear_time <= current_time <= self.appear_time + self.duration:
            progress = (current_time - self.appear_time) / (self.duration / self.repeats)
            segment = int(progress)
            reversed_direction = segment % 2 == 1
            segment_progress = progress - segment
            if reversed_direction:
                segment_progress = 1 - segment_progress
            fx = int(self.x1 + (self.x2 - self.x1) * segment_progress)
            fy = int(self.y1 + (self.y2 - self.y1) * segment_progress)
            ball_surf = sliderball_img.copy()
            ball_surf.set_alpha(alpha)
            screen.blit(ball_surf, ball_surf.get_rect(center=(fx, fy)))

    def check_hit(self, pos, current_time):
        if self.hit or self.missed:
            return 0
        # Check start circle hit within hit window
        if not self.clicked:
            if abs(current_time - self.appear_time) > self.hit_window:
                if current_time > self.appear_time + self.hit_window:
                    self.missed = True
                return 0
            dx = pos[0] - self.x1
            dy = pos[1] - self.y1
            if math.hypot(dx, dy) <= self.radius:
                self.clicked = True
                self.last_check_time = current_time
                return 0
        return 0

    def update(self, current_time, mouse_pos):
        if self.hit or self.missed or not self.clicked:
            return 0
        if current_time > self.appear_time + self.duration + self.hit_window:
            self.hit = True
            return 300

        if current_time - self.last_check_time < 50:
            return 0

        progress = (current_time - self.appear_time) / (self.duration / self.repeats)
        segment = int(progress)
        reversed_direction = segment % 2 == 1
        segment_progress = progress - segment
        if reversed_direction:
            segment_progress = 1 - segment_progress
        fx = int(self.x1 + (self.x2 - self.x1) * segment_progress)
        fy = int(self.y1 + (self.y2 - self.y1) * segment_progress)

        dist = math.hypot(mouse_pos[0] - fx, mouse_pos[1] - fy)
        self.last_check_time = current_time

        # Fail if mouse is too far from slider ball position
        if dist > self.follow_radius + 30:
            self.missed = True
            return 50

        return 0

def parse_osu_file(path):
    objects = []
    audio_filename = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    hit_objects_started = False
    for line in lines:
        if line.startswith("AudioFilename:"):
            audio_filename = line.split(":", 1)[1].strip()
        if line.strip() == "[HitObjects]":
            hit_objects_started = True
            continue
        if hit_objects_started and line.strip():
            parts = line.strip().split(",")
            if len(parts) >= 5:
                x, y, time_ = int(parts[0]), int(parts[1]), int(parts[2])
                obj_type = int(parts[3])
                if obj_type & 2:  # slider
                    slider_parts = parts[5].split("|")
                    if len(slider_parts) > 1:
                        x2, y2 = map(int, slider_parts[1].split(":"))
                    else:
                        x2, y2 = x, y
                    objects.append(Slider(x, y, x2, y2, time_))
                else:  # hitcircle
                    objects.append(Circle(x, y, time_))
    return objects, audio_filename

def extract_osz(file_path):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        folder = os.path.join(EXTRACT_FOLDER, os.path.splitext(os.path.basename(file_path))[0])
        os.makedirs(folder, exist_ok=True)
        zip_ref.extractall(folder)
    return folder

def folder_menu(folders):
    selected = 0
    while True:
        screen.fill((20, 20, 20))
        for i, name in enumerate(folders):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            text = font.render(name, True, color)
            screen.blit(text, (50, 100 + 40 * i))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(folders)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(folders)
                elif event.key == pygame.K_RETURN:
                    return folders[selected]

def osu_file_menu(folder, osu_files):
    selected = 0
    while True:
        screen.fill((20, 20, 20))
        title = font.render("Select Beatmap", True, (255, 255, 255))
        screen.blit(title, (50, 50))
        for i, name in enumerate(osu_files):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            text = font.render(name, True, color)
            screen.blit(text, (50, 100 + 40 * i))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(osu_files)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(osu_files)
                elif event.key == pygame.K_RETURN:
                    return osu_files[selected]

def play_game(objects, audio_path):
    running = True
    start_time = pygame.time.get_ticks()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    score_values = []
    while running:
        screen.fill((30, 30, 30))
        current_time = pygame.time.get_ticks() - start_time
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for obj in objects:
                    score_values.append(obj.check_hit(mouse_pos, current_time))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.mixer.music.stop()
                    return

        for obj in objects:
            if isinstance(obj, Slider):
                score_values.append(obj.update(current_time, mouse_pos))
            obj.draw(current_time)

        score = sum(score_values)
        total = len(score_values) * 300 if score_values else 1
        accuracy = 100.0 * score / total
        screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (10, 10))
        screen.blit(font.render(f"Accuracy: {accuracy:.2f}%", True, (255, 255, 255)), (10, 40))

        pygame.display.flip()
        clock.tick(60)

def main():
    os.makedirs(EXTRACT_FOLDER, exist_ok=True)
    # Extract all .osz in current dir
    for file in os.listdir('.'):
        if file.endswith('.osz'):
            extract_osz(file)

    while True:
        folders = [f for f in os.listdir(EXTRACT_FOLDER) if os.path.isdir(os.path.join(EXTRACT_FOLDER, f))]
        selected_folder = folder_menu(folders)
        if not selected_folder:
            break

        full_folder_path = os.path.join(EXTRACT_FOLDER, selected_folder)
        osu_files = [f for f in os.listdir(full_folder_path) if f.endswith('.osu')]
        if not osu_files:
            print("No .osu files found in selected folder")
            continue

        if len(osu_files) == 1:
            selected_osu = osu_files[0]
        else:
            selected_osu = osu_file_menu(full_folder_path, osu_files)
            if not selected_osu:
                continue

        osu_path = os.path.join(full_folder_path, selected_osu)
        objects, audio_filename = parse_osu_file(osu_path)
        audio_path = os.path.join(full_folder_path, audio_filename)
        play_game(objects, audio_path)

if __name__ == "__main__":
    main()
