import pygame
import zipfile
import os
import math

# Initialize pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("osu! clone")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)


CIRCLE_RADIUS = 64
FOLLOW_RADIUS = 32
HIT_WINDOW = 150
APPROACH_RATE = 700
EXTRACT_FOLDER = "extracted"
SKIN_FOLDER = "skins/default"
HIT_SOUNDS = {"normal": "hitnormal"}

# --- Loads images from skins folder ---
def load_image(name):
    path = os.path.join(SKIN_FOLDER, name)
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    else:
        #fallback
        surf = pygame.Surface((CIRCLE_RADIUS*2, CIRCLE_RADIUS*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 0, 0), (CIRCLE_RADIUS, CIRCLE_RADIUS), CIRCLE_RADIUS)
        return surf

# Skin elements used during gameplay
skin_images = {
    "hitcircle": load_image("hitcircle.png"),
    "overlay": load_image("hitcircleoverlay.png"),
    "approach": load_image("approachcircle.png"),
    "sliderstart": load_image("sliderstartcircle.png"),
    "sliderend": load_image("sliderendcircle.png"),
    "sliderball": load_image("sliderball.png"),
}

# Loads hitsound from skin folder
def load_sound(name):
    path = os.path.join(SKIN_FOLDER, name)
    return pygame.mixer.Sound(path) if os.path.exists(path) else None

hitsound = load_sound(HIT_SOUNDS["normal"])

# --- Circle object class ---
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
        if dt > APPROACH_RATE:
            return

        if dt < -HIT_WINDOW:
            self.missed = True
            return

        # Calculate approach scale
        approach_progress = max(0, min(1, 1 - dt / APPROACH_RATE))
        approach_scale = 1 + (1 - approach_progress)
        alpha = int(255 * approach_progress)

        # Draw approach circle
        approach = pygame.transform.scale(
            skin_images["approach"], (int(CIRCLE_RADIUS*2*approach_scale), int(CIRCLE_RADIUS*2*approach_scale))
        )
        approach.set_alpha(alpha)
        screen.blit(approach, approach.get_rect(center=(self.x, self.y)))

        # Draw hitcircle + overlay normally
        circle_img = pygame.transform.scale(skin_images["hitcircle"], (CIRCLE_RADIUS*2, CIRCLE_RADIUS*2))
        screen.blit(circle_img, circle_img.get_rect(center=(self.x, self.y)))

        overlay_img = pygame.transform.scale(skin_images["overlay"], (CIRCLE_RADIUS*2, CIRCLE_RADIUS*2))
        screen.blit(overlay_img, overlay_img.get_rect(center=(self.x, self.y)))

    def check_hit(self, pos, current_time):
        # Check timing and position
        if self.hit or self.missed:
            return 0
        if abs(current_time - self.time) > HIT_WINDOW:
            return 0
        if math.hypot(pos[0]-self.x, pos[1]-self.y) <= CIRCLE_RADIUS:
            self.hit = True
            if hitsound:
                hitsound.play()
            return 300
        return 0

# --- Slider object class ---
class Slider:
    def __init__(self, x1, y1, curve_points, time_, duration=1000):
        self.x1 = int(x1 * WIDTH / 512)
        self.y1 = int(y1 * HEIGHT / 384)
        self.curve_points = [(int(px * WIDTH / 512), int(py * HEIGHT / 384)) for px, py in curve_points]
        self.time = time_
        self.duration = duration
        self.clicked = False
        self.hit = False
        self.missed = False

    def draw(self, current_time):
        if self.hit or self.missed:
            return

        dt = self.time - current_time
        if dt > APPROACH_RATE:
            return

        if dt < -self.duration:
            self.missed = True
            return

        self.draw_slider_body()

        # Approach logic
        approach_progress = max(0, min(1, 1 - dt / APPROACH_RATE))
        approach_scale = 1 + (1 - approach_progress)
        alpha = int(255 * approach_progress)

        #Approach circle on slider start
        approach = pygame.transform.scale(
            skin_images["approach"], (int(CIRCLE_RADIUS*2*approach_scale), int(CIRCLE_RADIUS*2*approach_scale))
        )
        approach.set_alpha(alpha)
        screen.blit(approach, approach.get_rect(center=(self.x1, self.y1)))

        # Draw slider outline (white) and translucent fill
        if len(self.curve_points) >= 1:
            points = [(self.x1, self.y1)] + self.curve_points
            path_thickness = CIRCLE_RADIUS * 2

            # Create a transparent surface to draw the track
            path_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

            # Draw circles between points to simulate a round stroke
            for i in range(len(points) - 1):
                start = points[i]
                end = points[i + 1]
                dx, dy = end[0] - start[0], end[1] - start[1]
                dist = max(1, int(math.hypot(dx, dy)))
                for j in range(dist):
                    t = j / dist
                    x = int(start[0] + dx * t)
                    y = int(start[1] + dy * t)
                    pygame.draw.circle(path_surf, (255, 255, 255, 100), (x, y), CIRCLE_RADIUS)

            screen.blit(path_surf, (0, 0))

        # Draw slider start/end circles with alpha
        start_circle = pygame.transform.scale(skin_images["sliderstart"], (CIRCLE_RADIUS*2, CIRCLE_RADIUS*2))
        start_circle.set_alpha(alpha)
        screen.blit(start_circle, start_circle.get_rect(center=(self.x1, self.y1)))

        end_pos = self.curve_points[-1] if self.curve_points else (self.x1, self.y1)
        end_circle = pygame.transform.scale(skin_images["sliderend"], (CIRCLE_RADIUS*2, CIRCLE_RADIUS*2))
        end_circle.set_alpha(alpha)
        screen.blit(end_circle, end_circle.get_rect(center=end_pos))

        # Draw slider ball if clicked and held
        if self.clicked and self.time <= current_time <= self.time + self.duration:
            t = (current_time - self.time) / self.duration
            # Calculate position along curve (linear interpolation for now)
            pos = self.get_pos_along_curve(t)
            follow = pygame.transform.scale(skin_images["sliderball"], (FOLLOW_RADIUS*2, FOLLOW_RADIUS*2))
            screen.blit(follow, follow.get_rect(center=pos))

    def draw_slider_body(self):
        # Render slider path using trnslucent circles between points
        if len(self.curve_points) >= 1:
            points = [(self.x1, self.y1)] + self.curve_points
            path_thickness = CIRCLE_RADIUS * 2

            path_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

            for i in range(len(points) - 1):
                start = points[i]
                end = points[i + 1]
                dx, dy = end[0] - start[0], end[1] - start[1]
                dist = max(1, int(math.hypot(dx, dy)))
                for j in range(dist):
                    t = j / dist
                    x = int(start[0] + dx * t)
                    y = int(start[1] + dy * t)
                    pygame.draw.circle(path_surf, (255, 255, 255, 100), (x, y), CIRCLE_RADIUS)

            screen.blit(path_surf, (0, 0))

    def get_pos_along_curve(self, t):
        # Interpolates slider ball position based on time
        if len(self.curve_points) == 0:
            return (self.x1, self.y1)
        points = [(self.x1, self.y1)] + self.curve_points
        total_segments = len(points) - 1
        segment_t = t * total_segments
        segment_index = min(int(segment_t), total_segments - 1)
        local_t = segment_t - segment_index
        x0, y0 = points[segment_index]
        x1, y1 = points[segment_index + 1]
        x = int(x0 + (x1 - x0) * local_t)
        y = int(y0 + (y1 - y0) * local_t)
        return (x, y)

    def check_hit(self, pos, current_time):
        if self.hit or self.clicked or abs(current_time - self.time) > HIT_WINDOW:
            return 0
        if math.hypot(pos[0] - self.x1, pos[1] - self.y1) <= CIRCLE_RADIUS:
            self.clicked = True
            if hitsound:
                hitsound.play()  # <--- add this line here!
            return 100
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

# --- Parse .osu file to extract hit objects and audio ---
def parse_osu_file(path):
    objects = []
    audio_file = None
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    hitobjects_section = False
    timing_points_section = False
    for line in lines:
        line = line.strip()
        if line.startswith("AudioFilename:"):
            audio_file = line.split(":")[1].strip()
        if line == "[HitObjects]":
            hitobjects_section = True
            continue
        if hitobjects_section:
            if line == "":
                break
            parts = line.split(",")
            x, y, time_ = parts[0], parts[1], parts[2]
            obj_type = int(parts[3])
            if obj_type & 1:
                objects.append(Circle(int(x), int(y), int(time_)))
            elif obj_type & 2:
                # Slider parsing (simple linear slider)
                curve_str = parts[5]
                points = []
                if "|" in curve_str:
                    points = [p.split(":") for p in curve_str.split("|")[1:]]
                    points = [(int(px), int(py)) for px, py in points]
                slider_duration = 1000  # simple fixed duration
                objects.append(Slider(int(x), int(y), points, int(time_), slider_duration))
    return objects, audio_file

# --- Extract .osz (zip) files ---
def extract_osz(path):
    folder = os.path.join(EXTRACT_FOLDER, os.path.basename(path).replace(".osz", ""))
    if not os.path.exists(folder):
        with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(folder)
    return folder

# --- Accuracy calculation ---
def update_accuracy(scores):
    return 100 * sum(scores) / (300 * len(scores)) if scores else 100.0

# --- Lobby screen: beatmap selection ---
def lobby_menu():
    OSZ_FOLDER = "osz"
    if not os.path.exists(OSZ_FOLDER):
        os.makedirs(OSZ_FOLDER)
    files = [f for f in os.listdir(OSZ_FOLDER) if f.endswith(".osz")]
    if not files:
        print("No .osz files found in 'osz' folder. Please add your .osz files there.")
        pygame.quit()
        exit()

    selected = 0
    while True:
        screen.fill((30, 30, 30))
        title = font.render("Select Beatmap (.osz) - Use UP/DOWN and Enter", True, (255,255,255))
        screen.blit(title, (20,20))

        # Display all beatmap filenames
        for i, f in enumerate(files):
            color = (255, 255, 255) if i == selected else (180, 180, 180)
            text = font.render(f, True, color)
            screen.blit(text, (40, 80 + i*30))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(files)-1, selected + 1)
                elif event.key == pygame.K_RETURN:
                    return os.path.join(OSZ_FOLDER, files[selected])

# --- Difficulty selection menu ---
def difficulty_menu(folder):
    diffs = []
    for f in os.listdir(folder):
        if f.endswith(".osu"):
            diffs.append(f)
    if len(diffs) <= 1:
        return os.path.join(folder, diffs[0]) if diffs else None
    selected = 0
    while True:
        screen.fill((40, 40, 40))
        title = font.render("Select Difficulty - Use UP/DOWN and Enter", True, (255,255,255))
        screen.blit(title, (20, 20))
        for i, f in enumerate(diffs):
            color = (255,255,255) if i == selected else (180,180,180)
            text = font.render(f, True, color)
            screen.blit(text, (40, 80 + i*30))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(diffs)-1, selected + 1)
                elif event.key == pygame.K_RETURN:
                    return os.path.join(folder, diffs[selected])

# --- Game loop for playing a beatmap ---
def play_game(objects, audio_path):
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    start_time = pygame.time.get_ticks()

    score = 0
    scores = []

    running = True
    while running:
        current_time = pygame.time.get_ticks() - start_time
        screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_z, pygame.K_x):
                    pos = pygame.mouse.get_pos()
                    for obj in objects:
                        score_inc = obj.check_hit(pos, current_time)
                        if score_inc:
                            score += score_inc
                            scores.append(score_inc)

        # Update sliders for holding
        pos = pygame.mouse.get_pos()
        for obj in objects:
            if isinstance(obj, Slider):
                score_inc = obj.update(current_time, pos)
                if score_inc:
                    score += score_inc
                    scores.append(score_inc)

        # Draw objects
        for obj in objects:
            obj.draw(current_time)

        # Display accuracy
        acc = update_accuracy(scores)
        score_text = font.render(f"Score: {score}  Accuracy: {acc:.2f}%", True, (255, 255, 255))
        screen.blit(score_text, (10, HEIGHT - 40))

        pygame.display.flip()
        clock.tick(60)

# --- End screen to show score and allow retry ---
def end_screen(score, accuracy):
    waiting = True
    while waiting:
        screen.fill((0, 0, 0))
        end_text = font.render("Map Complete!", True, (255, 255, 255))
        score_text = font.render(f"Final Score: {score}", True, (255, 255, 255))
        acc_text = font.render(f"Accuracy: {accuracy:.2f}%", True, (255, 255, 255))
        cont_text = font.render("Press Enter to return to Lobby", True, (180, 180, 180))

        screen.blit(end_text, (WIDTH//2 - end_text.get_width()//2, HEIGHT//3))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//3 + 50))
        screen.blit(acc_text, (WIDTH//2 - acc_text.get_width()//2, HEIGHT//3 + 90))
        screen.blit(cont_text, (WIDTH//2 - cont_text.get_width()//2, HEIGHT//3 + 150))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    waiting = False

# --- Main function controlling flow ---
def main():
    os.makedirs(EXTRACT_FOLDER, exist_ok=True)
    while True:
        osz_path = lobby_menu()
        folder = extract_osz(osz_path)
        osu_path = difficulty_menu(folder)
        if osu_path is None:
            print("No difficulty found!")
            break

        objects, audio_file = parse_osu_file(osu_path)
        audio_path = os.path.join(folder, audio_file)

        score, acc = play_game(objects, audio_path)
        end_screen(score, acc)

if __name__ == "__main__":
    main()
