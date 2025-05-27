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


# Circle with skin support
class Circle:
    def __init__(self, x, y, appear_time, skin):
        self.x = int(x * WIDTH / 512)
        self.y = int(y * HEIGHT / 384)
        self.appear_time = appear_time
        self.hit = False
        self.radius = 64
        self.skin = skin

    def draw(self, current_time, skin=None):
        if self.hit or current_time < self.appear_time - 1000:
            return
        if current_time > self.appear_time + 500:
            self.hit = True
            return

        if skin and 'hitcircle' in skin:
            img = skin['hitcircle']
            rect = img.get_rect(center=(self.x, self.y))
            screen.blit(img, rect)
        else:
            pygame.draw.circle(screen, (255, 0, 0), (self.x, self.y), self.radius, 5)

        time_until_hit = self.appear_time - current_time
        if time_until_hit > 0:
            approach_radius = int(self.radius + 2 * self.radius * (time_until_hit / 1000))
            if skin and 'approachcircle' in skin:
                img = skin['approachcircle']
                rect = img.get_rect(center=(self.x, self.y))
                scale = approach_radius * 2 / img.get_width()
                img_scaled = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                rect = img_scaled.get_rect(center=(self.x, self.y))
                screen.blit(img_scaled, rect)
            else:
                pygame.draw.circle(screen, (0, 255, 0), (self.x, self.y), approach_radius, 2)
        time_until_hit = self.appear_time - current_time
        if time_until_hit > 0:
            scale = 1 + 2 * (time_until_hit / 1000)
            if self.skin and 'approachcircle' in self.skin:
                approach_img = pygame.transform.scale(
                    self.skin['approachcircle'],
                    (int(128 * scale), int(128 * scale))
                )
                rect = approach_img.get_rect(center=(self.x, self.y))
                screen.blit(approach_img, rect)
            else:
                approach_radius = int(self.radius + 2 * self.radius * (time_until_hit / 1000))
                pygame.draw.circle(screen, (0, 255, 0), (self.x, self.y), approach_radius, 2)

    def check_hit(self, pos, current_time):
        if self.hit or abs(current_time - self.appear_time) > 150:
            return 0
        dx, dy = pos[0] - self.x, pos[1] - self.y
        if math.hypot(dx, dy) <= self.radius:
            self.hit = True
            return 300
        return 0


# Slider (simple version, no skin support here)
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
        self.radius = 64
        self.follow_radius = 32
        self.last_check_time = 0

    def draw(self, current_time):
        if self.hit or current_time < self.appear_time - 1000:
            return
        pygame.draw.line(screen, (0, 255, 255), (self.x1, self.y1), (self.x2, self.y2), 10)
        pygame.draw.circle(screen, (0, 200, 200), (self.x1, self.y1), 16)
        pygame.draw.circle(screen, (0, 200, 200), (self.x2, self.y2), 16)
        time_until_hit = self.appear_time - current_time
        if time_until_hit > 0:
            approach_radius = int(self.radius + 2 * self.radius * (time_until_hit / 1000))
            pygame.draw.circle(screen, (0, 255, 0), (self.x1, self.y1), approach_radius, 2)
        if self.appear_time <= current_time <= self.appear_time + self.duration:
            progress = (current_time - self.appear_time) / (self.duration / self.repeats)
            segment = int(progress)
            reversed_direction = segment % 2 == 1
            segment_progress = progress - segment
            if reversed_direction:
                segment_progress = 1 - segment_progress
            fx = int(self.x1 + (self.x2 - self.x1) * segment_progress)
            fy = int(self.y1 + (self.y2 - self.y1) * segment_progress)
            pygame.draw.circle(screen, (255, 255, 255), (fx, fy), self.follow_radius, 3)

    def check_hit(self, pos, current_time):
        if self.hit:
            return 0
        if not self.clicked and abs(current_time - self.appear_time) < 150:
            dx = pos[0] - self.x1
            dy = pos[1] - self.y1
            if math.hypot(dx, dy) <= self.radius:
                self.clicked = True
                self.last_check_time = current_time
                return 0
        return 0

    def update(self, current_time, mouse_pos):
        if self.hit or not self.clicked:
            return 0
        if current_time > self.appear_time + self.duration:
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
        if dist > self.follow_radius + 30:
            self.hit = True
            return 50
        return 0


# Parse .osu file for circles and sliders
def parse_osu_file(path, skin):
    objects = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    hit_objects_started = False
    for line in lines:
        if line.strip() == "[HitObjects]":
            hit_objects_started = True
            continue
        if hit_objects_started:
            if not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) >= 5:
                x, y, time_ = int(parts[0]), int(parts[1]), int(parts[2])
                obj_type = int(parts[3])
                if obj_type & 2:
                    slider_parts = parts[5].split("|")
                    if len(slider_parts) > 1:
                        x2, y2 = map(int, slider_parts[1].split(":"))
                    else:
                        x2, y2 = x, y
                    objects.append(Slider(x, y, x2, y2, time_))
                else:
                    objects.append(Circle(x, y, time_, skin))
    return objects


# Score and accuracy
def update_accuracy(score_values):
    if not score_values:
        return 100.0
    total = len(score_values) * 300
    score = sum(score_values)
    return 100.0 * score / total


# Load skin images from folder
def load_skin(skin_folder):
    skin = {}
    try:
        hitcircle = pygame.image.load(os.path.join(skin_folder, "hitcircle.png")).convert_alpha()
        approachcircle = pygame.image.load(os.path.join(skin_folder, "approachcircle.png")).convert_alpha()
        skin['hitcircle'] = pygame.transform.smoothscale(hitcircle, (128, 128))
        skin['approachcircle'] = pygame.transform.smoothscale(approachcircle, (128, 128))
    except Exception as e:
        print(f"Skin loading failed or missing images: {e}")
        return None
    return skin


# Gameplay loop
def play_game(objects, audio_path):
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    score_values = []
    running = True

    while running:
        current_time = pygame.mixer.music.get_pos()  # synced time in ms
        screen.fill((30, 30, 30))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                return False  # quit whole program
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.mixer.music.stop()
                    return True  # exit to menu
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for obj in objects:
                    score_values.append(obj.check_hit(mouse_pos, current_time))

        for obj in objects:
            if isinstance(obj, Slider):
                score_values.append(obj.update(current_time, mouse_pos))
            obj.draw(current_time)

        score = sum(score_values)
        accuracy = update_accuracy(score_values)

        screen.blit(font.render(f"Score: {score}", True, (255, 255, 255)), (10, 10))
        screen.blit(font.render(f"Accuracy: {accuracy:.2f}%", True, (255, 255, 255)), (10, 40))

        pygame.display.flip()
        clock.tick(60)


# Extract .osz files
def extract_osz(file_path):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        folder = os.path.join(EXTRACT_FOLDER, os.path.splitext(os.path.basename(file_path))[0])
        os.makedirs(folder, exist_ok=True)
        zip_ref.extractall(folder)
    return folder


# Select beatmap folder
def lobby_menu():
    screen.fill((15, 15, 15))
    text = font.render("Press number key to select beatmap:", True, (255, 255, 255))
    screen.blit(text, (10, 10))

    files = [f for f in os.listdir('.') if f.endswith('.osz')]
    if not files:
        screen.blit(font.render("No .osz files found in current directory.", True, (255, 0, 0)), (10, 50))
        pygame.display.flip()
        pygame.time.wait(2000)
        return None

    for i, f in enumerate(files):
        item = font.render(f"{i + 1}. {f}", True, (200, 200, 200))
        screen.blit(item, (10, 40 + i * 30))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(files):
                        return files[idx]
                elif event.key == pygame.K_ESCAPE:
                    return None
        clock.tick(60)


def main():
    os.makedirs(EXTRACT_FOLDER, exist_ok=True)
    running = True
    while running:
        selected_osz = lobby_menu()
        if selected_osz is None:
            break  # user quit

        extracted_folder = extract_osz(selected_osz)
        osu_files = [f for f in os.listdir(extracted_folder) if f.endswith(".osu")]
        if not osu_files:
            print("No .osu files found in extracted folder.")
            continue

        skin_folder = os.path.join(extracted_folder, "skin")
        skin = load_skin(skin_folder)

        osu_path = os.path.join(extracted_folder, osu_files[0])

        # Find audio file
        audio_path = None
        for f in os.listdir(extracted_folder):
            if f.endswith(".mp3") or f.endswith(".ogg"):
                audio_path = os.path.join(extracted_folder, f)
                break

        if not audio_path:
            print("No audio file found in extracted beatmap.")
            continue

        objects = parse_osu_file(osu_path, skin)
        exited_normally = play_game(objects, audio_path)
        if not exited_normally:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
