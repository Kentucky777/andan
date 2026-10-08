"""
Простая игра Пинг-понг (Pong) на pygame
Управление:
  Игрок 1 (левая ракетка): W (вверх), S (вниз)
  Игрок 2 (правая ракетка): стрелка вверх, стрелка вниз
"""

import pygame
import sys

# Инициализация pygame
pygame.init()

# Настройки экрана
WIDTH, HEIGHT = 800, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Пинг-понг")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Параметры ракеток
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 90
PADDLE_SPEED = 6

left_paddle = pygame.Rect(30, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
right_paddle = pygame.Rect(WIDTH - 30 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)

# Параметры мяча
BALL_SIZE = 15
ball = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
ball_speed_x = 5
ball_speed_y = 5

# Счёт
score_left = 0
score_right = 0
WIN_SCORE = 3  # до скольки очков играем
font = pygame.font.SysFont(None, 60)
big_font = pygame.font.SysFont(None, 90)

clock = pygame.time.Clock()
game_over = False
winner_text = ""


def reset_ball():
    """Возвращает мяч в центр после гола"""
    ball.center = (WIDTH // 2, HEIGHT // 2)
    return -ball_speed_x  # меняем направление после гола


running = True
while running:
    # Обработка событий (закрытие окна)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if game_over:
        # Экран окончания игры
        screen.fill(BLACK)
        text = big_font.render(winner_text, True, WHITE)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 60))
        hint = font.render("Игра закроется через 3 секунды", True, WHITE)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 20))
        pygame.display.flip()
        pygame.time.wait(3000)  # ждём 3 секунды
        running = False
        continue

    # Управление ракетками
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] and left_paddle.top > 0:
        left_paddle.y -= PADDLE_SPEED
    if keys[pygame.K_s] and left_paddle.bottom < HEIGHT:
        left_paddle.y += PADDLE_SPEED
    if keys[pygame.K_UP] and right_paddle.top > 0:
        right_paddle.y -= PADDLE_SPEED
    if keys[pygame.K_DOWN] and right_paddle.bottom < HEIGHT:
        right_paddle.y += PADDLE_SPEED

    # Движение мяча
    ball.x += ball_speed_x
    ball.y += ball_speed_y

    # Отскок от верхней и нижней границы
    if ball.top <= 0 or ball.bottom >= HEIGHT:
        ball_speed_y *= -1

    # Отскок от ракеток
    if ball.colliderect(left_paddle) or ball.colliderect(right_paddle):
        ball_speed_x *= -1

    # Гол в левые ворота (мяч ушёл за левый край)
    if ball.left <= 0:
        score_right += 1
        ball_speed_x = reset_ball()

    # Гол в правые ворота (мяч ушёл за правый край)
    if ball.right >= WIDTH:
        score_left += 1
        ball_speed_x = reset_ball()

    # Проверка на победу
    if score_left >= WIN_SCORE:
        game_over = True
        winner_text = "Игрок 1 победил!"
    elif score_right >= WIN_SCORE:
        game_over = True
        winner_text = "Игрок 2 победил!"

    # Отрисовка
    screen.fill(BLACK)
    pygame.draw.rect(screen, WHITE, left_paddle)
    pygame.draw.rect(screen, WHITE, right_paddle)
    pygame.draw.ellipse(screen, WHITE, ball)
    pygame.draw.aaline(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))  # центральная линия

    # Вывод счёта
    score_text = font.render(f"{score_left}   {score_right}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 20))

    pygame.display.flip()
    clock.tick(60)  # 60 кадров в секунду

pygame.quit()
sys.exit()