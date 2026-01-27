import pygame
import sys
import webbrowser
import json
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("HEX Yield Visualizer")

# Set custom window icon
icon = pygame.image.load("HEX.png")
pygame.display.set_icon(icon)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
BLUE = (70, 130, 180)

# Game settings
coins_per_day = 25000  # Default value
fall_speed = 4
fallen_count = 0
settings_open = False  # Track if settings menu is open
sound_enabled = True  # Track if sound is enabled
volume = 0.15  # Volume level (0.0 to 1.0)

# Coin spawn point (fixed position at top center)
COIN_SPAWN_X = WIDTH // 2
COIN_SPAWN_Y = -50

# Piggy bank position (bottom center)
PIGGY_BANK_X = WIDTH // 2
PIGGY_BANK_Y = HEIGHT - 100


class Coin:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.image = image
        self.width = image.get_width()
        self.height = image.get_height()

    def update(self):
        self.y += fall_speed

    def draw(self, surface):
        rect = self.image.get_rect(center=(self.x, self.y))
        surface.blit(self.image, rect)

    def is_in_piggy_bank(self):
        # Check if coin has reached the piggy bank
        return self.y >= PIGGY_BANK_Y - 65


class InputBox:
    def __init__(self, x, y, w, h, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.color_inactive = GRAY
        self.color_active = LIGHT_GRAY
        self.color = self.color_inactive
        self.text = str(coins_per_day)
        self.active = False
        self.font = pygame.font.Font("arial.ttf", 26)
        self.cursor_pos = len(self.text)  # Cursor position
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        global coins_per_day

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Toggle active state
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.color = self.color_active
                # Calculate cursor position based on click location
                click_x = event.pos[0] - (self.rect.x + 10)
                # Estimate character position
                for i in range(len(self.text) + 1):
                    text_width = self.font.size(self.text[:i])[0]
                    if click_x <= text_width + self.font.size(self.text[i:i + 1])[0] / 2 if i < len(
                            self.text) else True:
                        self.cursor_pos = i
                        break
            else:
                self.active = False
                self.color = self.color_inactive

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                # Update coins per day (both Enter keys work)
                try:
                    value = int(self.text)
                    if value > 0:
                        coins_per_day = value
                        save_settings()
                    else:
                        self.text = str(coins_per_day)
                        self.cursor_pos = len(self.text)
                except ValueError:
                    self.text = str(coins_per_day)
                    self.cursor_pos = len(self.text)
                self.active = False
                self.color = self.color_inactive

            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1

            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]

            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)

            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)

            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0

            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)

            else:
                # Only allow digits
                if event.unicode.isdigit():
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += 1

    def update_text(self):
        """Update the text to match current coins_per_day value"""
        if not self.active:
            self.text = str(coins_per_day)
            self.cursor_pos = len(self.text)

    def update(self, dt):
        """Update cursor blinking"""
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 500:  # Blink every 500ms
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        else:
            self.cursor_visible = True
            self.cursor_timer = 0

    def draw(self, surface):
        # Draw label
        label_text = self.font.render(self.label, True, WHITE)
        surface.blit(label_text, (self.rect.x, self.rect.y - 35))

        # Draw input box
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=5)

        # Draw text
        text_surface = self.font.render(self.text, True, BLACK)
        surface.blit(text_surface, (self.rect.x + 10, self.rect.y + 4))

        # Draw cursor if active
        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + 10 + self.font.size(self.text[:self.cursor_pos])[0]
            cursor_y = self.rect.y + 4
            cursor_height = self.font.get_height()
            pygame.draw.line(surface, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)

        # Draw instruction
        if self.active:
            instruction = self.font.render("Press Enter to confirm", True, LIGHT_GRAY)
        else:
            instruction = self.font.render("Click to edit", True, GRAY)
        surface.blit(instruction, (self.rect.x + self.rect.width + 20, self.rect.y + 4))


class Checkbox:
    def __init__(self, x, y, size, label):
        self.rect = pygame.Rect(x, y, size, size)
        self.label = label
        self.checked = sound_enabled
        self.font = pygame.font.Font("arial.ttf", 26)
        self.size = size

    def handle_event(self, event):
        global sound_enabled

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked
                sound_enabled = self.checked
                save_settings()
                return True
        return False

    def update_state(self):
        """Update checkbox to match current sound_enabled state"""
        self.checked = sound_enabled

    def draw(self, surface):
        # Draw checkbox box
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=3)

        # Draw checkmark if checked
        if self.checked:
            # Draw an X checkmark
            margin = 5
            pygame.draw.line(surface, WHITE,
                             (self.rect.x + margin, self.rect.y + margin),
                             (self.rect.right - margin, self.rect.bottom - margin), 3)
            pygame.draw.line(surface, WHITE,
                             (self.rect.right - margin, self.rect.y + margin),
                             (self.rect.x + margin, self.rect.bottom - margin), 3)

        # Draw label
        label_text = self.font.render(self.label, True, WHITE)
        surface.blit(label_text, (self.rect.right + 15, self.rect.y + (self.size - label_text.get_height()) // 2))


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.dragging = False
        self.handle_radius = 10
        self.font = pygame.font.Font("arial.ttf", 24)

    def handle_event(self, event):
        global volume

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            handle_x = self.rect.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
            handle_y = self.rect.centery

            if ((mouse_x - handle_x) ** 2 + (mouse_y - handle_y) ** 2) ** 0.5 <= self.handle_radius:
                self.dragging = True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
            save_settings()

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mouse_x = event.pos[0]
            rel_x = max(0, min(mouse_x - self.rect.x, self.rect.width))
            self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
            volume = self.value
            cha_ching_sound.set_volume(volume)

    def draw(self, surface):
        # Draw label with percentage
        label_text = self.font.render(f"{self.label}: {int(self.value * 100)}%", True, WHITE)
        surface.blit(label_text, (self.rect.x, self.rect.y - 30))

        # Draw track
        pygame.draw.rect(surface, GRAY, self.rect, border_radius=5)

        # Draw handle
        handle_x = self.rect.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
        pygame.draw.circle(surface, WHITE, (int(handle_x), self.rect.centery), self.handle_radius)
        pygame.draw.circle(surface, LIGHT_GRAY, (int(handle_x), self.rect.centery), self.handle_radius - 2)


class LinkButton:
    def __init__(self, x, y, w, h, text, url):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.url = url
        self.font = pygame.font.Font("arial.ttf", 26)
        self.hovered = False
        self.color = BLUE
        self.hover_color = (100, 160, 220)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                webbrowser.open(self.url)
                return True
        return False

    def draw(self, surface):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=5)

        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class SettingsButton:
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.hovered = False
        self.hover_brightness = 1.0

    def handle_event(self, event):
        global settings_open

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                settings_open = not settings_open
                return True
        return False

    def draw(self, surface):
        # Create a brighter version when hovered
        if self.hovered:
            bright_image = self.image.copy()
            bright_image.fill((100, 100, 100), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(bright_image, self.rect)
        else:
            bright_image = self.image.copy()
            bright_image.fill((50, 50, 50), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(bright_image, self.rect)

    def update_position(self, x, y):
        """Update button position when window is resized"""
        self.rect.x = x
        self.rect.y = y


class SettingsMenu:
    def __init__(self):
        self.width = 500
        self.height = 400
        self.x = (WIDTH - self.width) // 2
        self.y = (HEIGHT - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.font = pygame.font.Font("arial.ttf", 30)
        self.title_font = pygame.font.Font("arial.ttf", 40)

        # Create input box positioned within the menu
        self.input_box = InputBox(self.x + 50, self.y + 115, 150, 40, "HEX yield per day:")

        # Create sound checkbox
        self.sound_checkbox = Checkbox(self.x + 50, self.y + 180, 30, "Enable Sound")

        # Create volume slider
        self.volume_slider = Slider(self.x + 50, self.y + 250, 200, 20, 0.0, 1.0, volume, "Volume")

        # Create music playlist link
        self.music_link = LinkButton(self.x + 50, self.y + 310, 400, 40,
                                     "HEX Stake & Chill Music Playlist",
                                     "https://www.youtube.com/playlist?list=PLwvFQ9vlHH8xsRoQFV3A6VuWCb8tIwUa1")

        # Close button
        self.close_button = pygame.Rect(self.x + self.width - 40, self.y + 10, 30, 30)

    def handle_event(self, event):
        global settings_open

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if close button clicked
            if self.close_button.collidepoint(event.pos):
                settings_open = False
                return
            # Check if clicked outside menu
            if not self.rect.collidepoint(event.pos):
                settings_open = False
                return

        # Pass event to controls
        if not self.sound_checkbox.handle_event(event):
            if not self.volume_slider.handle_event(event):
                if not self.music_link.handle_event(event):
                    self.input_box.handle_event(event)

    def draw(self, surface):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        surface.blit(overlay, (0, 0))

        # Draw menu background
        pygame.draw.rect(surface, (40, 40, 40), self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 3, border_radius=10)

        # Draw title
        title = self.title_font.render("Settings", True, WHITE)
        title_rect = title.get_rect(center=(self.x + self.width // 2, self.y + 40))
        surface.blit(title, title_rect)

        # Draw input box
        self.input_box.update_text()
        self.input_box.draw(surface)

        # Draw sound checkbox
        self.sound_checkbox.update_state()
        self.sound_checkbox.draw(surface)

        # Draw volume slider
        self.volume_slider.draw(surface)

        # Draw music link
        self.music_link.draw(surface)

        # Draw close button
        pygame.draw.rect(surface, (200, 50, 50), self.close_button, border_radius=5)
        pygame.draw.line(surface, WHITE,
                         (self.close_button.x + 8, self.close_button.y + 8),
                         (self.close_button.x + 22, self.close_button.y + 22), 3)
        pygame.draw.line(surface, WHITE,
                         (self.close_button.x + 22, self.close_button.y + 8),
                         (self.close_button.x + 8, self.close_button.y + 22), 3)

    def update(self, dt):
        """Update input box cursor"""
        self.input_box.update(dt)

    def reposition(self, width, height):
        """Reposition menu and all controls when window is resized"""
        self.x = (width - self.width) // 2
        self.y = (height - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Reposition all controls
        self.input_box.rect.x = self.x + 50
        self.input_box.rect.y = self.y + 100

        self.sound_checkbox.rect.x = self.x + 50
        self.sound_checkbox.rect.y = self.y + 170

        self.volume_slider.rect.x = self.x + 50
        self.volume_slider.rect.y = self.y + 240

        self.music_link.rect.x = self.x + 50
        self.music_link.rect.y = self.y + 300

        self.close_button = pygame.Rect(self.x + self.width - 40, self.y + 10, 30, 30)


def save_settings():
    """Save settings to a JSON file"""
    settings = {
        'coins_per_day': coins_per_day,
        'sound_enabled': sound_enabled,
        'volume': volume
    }
    try:
        with open('hex_visualizer_settings.json', 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")


def load_settings():
    """Load settings from JSON file"""
    global coins_per_day, sound_enabled, volume

    if os.path.exists('hex_visualizer_settings.json'):
        try:
            with open('hex_visualizer_settings.json', 'r') as f:
                settings = json.load(f)
                coins_per_day = settings.get('coins_per_day', 25000)
                sound_enabled = settings.get('sound_enabled', True)
                volume = settings.get('volume', 0.15)
                print("Settings loaded successfully")
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use defaults if loading fails
            coins_per_day = 25000
            sound_enabled = True
            volume = 0.15
    else:
        print("No saved settings found, using defaults")


def load_coin_image():
    """Load coin image from file"""
    image = pygame.image.load("HEX.png")
    # Scale to reasonable size if needed
    if image.get_width() > 100 or image.get_height() > 100:
        image = pygame.transform.scale(image, (50, 50))
    return image


def load_piggy_bank_image():
    """Load piggy bank image from file"""
    image = pygame.image.load("piggy_bank.png")
    # Scale to reasonable size if needed
    if image.get_width() > 200 or image.get_height() > 200:
        image = pygame.transform.scale(image, (150, 120))
    return image


def load_settings_button_image():
    """Load settings button image from file"""
    image = pygame.image.load("settings_button.png")
    # Scale to reasonable size if needed (50x50 default)
    if image.get_width() > 60 or image.get_height() > 60:
        image = pygame.transform.scale(image, (50, 50))
    return image


def load_cha_ching_sound():
    """Load cha-ching sound from file"""
    sound = pygame.mixer.Sound("cha_ching.wav")
    sound.set_volume(volume)
    return sound


def calculate_spawn_interval(coins_per_day):
    """Calculate milliseconds between spawns based on coins per day"""
    # Milliseconds in a day
    ms_per_day = 24 * 60 * 60 * 1000  # 86,400,000 milliseconds
    if coins_per_day <= 0:
        return ms_per_day  # Fallback to 1 per day
    ms_per_coin = ms_per_day / coins_per_day
    return ms_per_coin


# Load saved settings
load_settings()

# Create image and sounds
coin_image = load_coin_image()
piggy_bank_image = load_piggy_bank_image()
settings_button_image = load_settings_button_image()
cha_ching_sound = load_cha_ching_sound()

# Create settings button and menu
settings_button = SettingsButton(WIDTH - 70, HEIGHT - 70, settings_button_image)
settings_menu = SettingsMenu()

# Main game loop
coins = []
clock = pygame.time.Clock()
frame_count = 0
running = True
last_spawn_time = pygame.time.get_ticks() - calculate_spawn_interval(coins_per_day)  # Start with first coin ready

print("HEX Yield Visualizer")
print("Place your custom images and sound in the same folder as this script:")
print("Close the window to exit")

while running:
    # Get delta time for cursor blinking
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.VIDEORESIZE:
            # Update screen dimensions
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

            # Update coin spawn position
            COIN_SPAWN_X = WIDTH // 2

            # Update piggy bank position
            PIGGY_BANK_X = WIDTH // 2
            PIGGY_BANK_Y = HEIGHT - 100

            # Update settings button position
            settings_button.update_position(WIDTH - 70, HEIGHT - 70)

            # Reposition settings menu
            settings_menu.reposition(WIDTH, HEIGHT)

        # Handle settings menu or button events
        if settings_open:
            settings_menu.handle_event(event)
        else:
            settings_button.handle_event(event)

    # Get current time in milliseconds
    current_time = pygame.time.get_ticks()

    # Calculate spawn interval based on coins per day (in milliseconds)
    spawn_interval = calculate_spawn_interval(coins_per_day)

    # Spawn new coins based on actual time elapsed
    if current_time - last_spawn_time >= spawn_interval:
        new_coin = Coin(COIN_SPAWN_X, COIN_SPAWN_Y, coin_image)
        coins.append(new_coin)
        last_spawn_time = current_time

    # Update coins
    coins_to_remove = []
    for coin in coins:
        coin.update()
        if coin.is_in_piggy_bank():
            coins_to_remove.append(coin)
            if sound_enabled:
                cha_ching_sound.play()
            fallen_count += 1

    # Remove offscreen coins
    for coin in coins_to_remove:
        coins.remove(coin)

    # Update settings menu if open
    if settings_open:
        settings_menu.update(dt)

    # Draw everything
    screen.fill(BLACK)

    # Draw piggy bank
    piggy_rect = piggy_bank_image.get_rect(center=(PIGGY_BANK_X, PIGGY_BANK_Y))
    screen.blit(piggy_bank_image, piggy_rect)

    # Draw coins
    for coin in coins:
        coin.draw(screen)

    # Draw counter
    font = pygame.font.Font("impact.ttf", 36)
    counter_text = font.render(f"HEX Yield: {fallen_count}", True, WHITE)
    screen.blit(counter_text, (10, HEIGHT - 50))

    # Draw settings button
    settings_button.draw(screen)

    # Draw settings menu if open
    if settings_open:
        settings_menu.draw(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()