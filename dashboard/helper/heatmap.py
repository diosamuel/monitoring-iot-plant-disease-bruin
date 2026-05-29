from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

def drawHeatmap(input_path,pixel_locations,point_size=60,alpha=0.5):
    image = Image.open(input_path).convert("RGB")
    img_array = np.array(image)
    height, width = img_array.shape[:2]
    heatmap = np.zeros((height, width))
    for x, y in pixel_locations:
        y_grid, x_grid = np.ogrid[:height, :width]

        distance = (
            (x_grid - x) ** 2 +
            (y_grid - y) ** 2
        )

        gaussian = np.exp(
            -distance / (2 * point_size ** 2)
        )

        heatmap += gaussian
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    fig = plt.figure(figsize=(8, 10))
    plt.imshow(img_array)
    plt.imshow(
        heatmap,
        cmap="jet",
        alpha=alpha
    )
    plt.axis("off")
    buffer = BytesIO()
    plt.savefig(
        buffer,
        format="png",
        bbox_inches="tight",
        pad_inches=0
    )
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()