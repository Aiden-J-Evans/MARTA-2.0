from openai import OpenAI
client = OpenAI()

response = client.images.generate(
  model="dall-e-3",
  prompt="2D grass texture",
  size="512x512",
  quality="standard",
  n=1,
)

image_url = response.data[0].url
print(image_url)