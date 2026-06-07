import cv2
import numpy as np
import matplotlib.pyplot as plt

def generateHeatmap(image,pixel_location):
    img = cv2.imread(image)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)
    sigma = 50
    # Create gaussian hotspot for each point
    y_grid, x_grid = np.mgrid[0:h, 0:w]
    for x, y in pixel_location:
        gaussian = np.exp(
            -((x_grid - x) ** 2 + (y_grid - y) ** 2)
            / (2 * sigma**2)
        )
        heatmap += gaussian
    # Normalize
    heatmap /= heatmap.max()
    # Plot
    plt.figure(figsize=(10, 8))
    plt.imshow(img)
    plt.imshow(
        heatmap,
        cmap="jet",
        alpha=0.5
    )
    
    plt.axis("off")
    return plt