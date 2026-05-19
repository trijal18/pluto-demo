import pygame
import time
import sys
import os

# Ensure we can import plutov2 from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plutov2 import PlutoV2


def clamp(value, minimum=1000, maximum=2000):
    return max(minimum, min(maximum, value))


def main():

    pygame.init()

    # Small window just for keyboard focus
    screen = pygame.display.set_mode((500, 200))
    pygame.display.set_caption("Pluto Drone Keyboard Control")

    font = pygame.font.SysFont(None, 28)

    drone = PlutoV2()

    print("\n--- KEYBOARD PILOT ACTIVE ---")
    print("------------------------------")
    print("W / S      : Throttle UP/DOWN")
    print("Q / E      : Yaw LEFT/RIGHT")
    print("I / K      : Pitch FORWARD/BACK")
    print("J / L      : Roll LEFT/RIGHT")
    print("A           : ARM")
    print("D           : DISARM")
    print("T           : TAKEOFF")
    print("G           : LAND")
    print("SPACE       : NEUTRALIZE")
    print("ESC         : EXIT")
    print("------------------------------")

    # Neutral RC values
    r = 1500
    p = 1500
    t = 1000
    y = 1500

    print("Connecting to drone...")
    drone.connect()

    clock = pygame.time.Clock()

    running = True

    try:

        while running and drone.connected:

            # Handle events
            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:

                    # Exit
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    # ARM / DISARM
                    elif event.key == pygame.K_a:
                        drone.arm()

                    elif event.key == pygame.K_d:
                        drone.disarm()

                    # TAKEOFF / LAND
                    elif event.key == pygame.K_t:
                        drone.takeoff()

                    elif event.key == pygame.K_g:
                        drone.land()

                    # Reset
                    elif event.key == pygame.K_SPACE:
                        r, p, t, y = 1500, 1500, 1000, 1500

            # Continuous key press handling
            keys = pygame.key.get_pressed()

            # Throttle
            if keys[pygame.K_w]:
                t += 10

            if keys[pygame.K_s]:
                t -= 10

            # Yaw
            if keys[pygame.K_q]:
                y -= 20

            if keys[pygame.K_e]:
                y += 20

            # Pitch
            if keys[pygame.K_i]:
                p += 20

            if keys[pygame.K_k]:
                p -= 20

            # Roll
            if keys[pygame.K_j]:
                r -= 20

            if keys[pygame.K_l]:
                r += 20

            # Clamp values
            r = clamp(r)
            p = clamp(p)
            t = clamp(t)
            y = clamp(y)

            # Send RC commands
            drone.set_rc(
                roll=r,
                pitch=p,
                throttle=t,
                yaw=y
            )

            # Telemetry
            state = drone.get_state()

            telemetry = (
                f"R:{r} P:{p} T:{t} Y:{y} | "
                f"Battery:{state['battery']:.2f}V | "
                f"Alt:{state['height']}cm"
            )

            print("\r" + telemetry + "   ", end="")

            # Draw window
            screen.fill((0, 0, 0))

            text = font.render(
                "Drone Keyboard Control Active",
                True,
                (255, 255, 255)
            )

            screen.blit(text, (80, 80))

            pygame.display.flip()

            # 30 FPS control loop
            clock.tick(30)

    except Exception as e:
        print(f"\nError: {e}")

    finally:

        print("\nStopping...")

        try:
            drone.disarm()
            drone.disconnect()
        except:
            pass

        pygame.quit()


if __name__ == "__main__":
    main()