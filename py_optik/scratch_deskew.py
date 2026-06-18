import cv2
import numpy as np

img_path = r"C:\Users\erd5334\Desktop\Ali Yazıcı\optik\optikForm\py_optik\temp_images\DTİCBBP_33.jpg"

image = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

edges = cv2.Canny(gray, 50, 150, apertureSize=3)
lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=20)

angles = []
if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -45 <= angle <= 45: angles.append(angle)
        elif angle > 45: angles.append(angle - 90)
        elif angle < -45: angles.append(angle + 90)
        
print("HoughLinesP Median Angle:", np.median(angles) if angles else "None")

# MinAreaRect Method
gray_inv = cv2.bitwise_not(gray)
thresh = cv2.threshold(gray_inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
coords = np.column_stack(np.where(thresh > 0))
angle = cv2.minAreaRect(coords)[-1]
if angle < -45: angle = -(90 + angle)
else: angle = -angle
print("MinAreaRect Angle:", angle)

# Standard Hough Lines
lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
angles2 = []
if lines is not None:
    for line in lines:
        rho, theta = line[0]
        a = np.degrees(theta)
        if 45 <= a <= 135: angles2.append(a - 90)
        elif a <= 45: angles2.append(a)
        elif a >= 135: angles2.append(a - 180)
print("Standard Hough Median Angle:", np.median(angles2) if angles2 else "None")

def score_angle(thresh_img, angle):
    (h, w) = thresh_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(thresh_img, M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    proj = np.sum(rotated, axis=1)
    return np.var(proj)

def fallback_deskew(thresh):
    coarse_angles = np.arange(-5.0, 5.0, 0.5)
    best_coarse = 0
    max_score = 0
    for a in coarse_angles:
        score = score_angle(thresh, a)
        if score > max_score: max_score = score; best_coarse = a
    fine_angles = np.arange(best_coarse - 0.5, best_coarse + 0.5, 0.05)
    best_angle = 0
    max_score = 0
    for a in fine_angles:
        score = score_angle(thresh, a)
        if score > max_score: max_score = score; best_angle = a
    return best_angle

print("Fallback Variance Angle:", fallback_deskew(thresh))

