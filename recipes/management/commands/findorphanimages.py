import os

from Levenshtein import distance

from django.core.management.base import BaseCommand
from django.conf import settings

from recipes.models import Mix


def find_closest_by_name(name, candidates):
    distances = [distance(name, candidate) for candidate in candidates]
    min_index, dist = min(enumerate(distances), key=lambda p: p[1])
    return candidates[min_index], dist

def find_name_similar(name, candidates):
    for candidate in candidates:
        if candidate.startswith(name):
            return candidate

class Command(BaseCommand):
    help = 'List all uploaded mix images that are not used anymore'

    def handle(self, *args, **options):
        directory = os.path.join(settings.MEDIA_ROOT, settings.UPLOAD_FOR_MIX)
        images = sorted(list(os.walk(directory))[0][2])
        mixes_raw = Mix.objects.order_by('image').values_list('image', flat=True)
        mixes_images = [os.path.basename(im) for im in mixes_raw if im]
        print('You have', len(images), 'uploaded images and', len(mixes_images), 'mixes use an image. Sample of images', images[:10], 'and sample of mix images', mixes_images[:10])
        print('Images not used by a mix', sorted(list(set(images) - set(mixes_images))))
        print('Mixes with no image', list(Mix.objects.filter(image='')))
        images_no_extension = [image_with_extension[:-4] for image_with_extension in images]
        for image in images_no_extension:
            similar = find_name_similar(image, list(set(images_no_extension) - set((image,))))
            if similar:
                #print(image, similar)
                try:
                    mix = Mix.objects.get(image=os.path.join(settings.UPLOAD_FOR_MIX, similar + '.jpg'))
                    print('This mix', mix, 'uses the image', mix.image, 'but', image + '.jpg', 'is available')
                    r = input('Would you like to replace it? (type y) ')
                    if r == 'y':
                        new_i = os.path.join(settings.UPLOAD_FOR_MIX, image + '.jpg')
                        mix.image = new_i
                        mix.save()
                        print('replaced', mix.image, 'with', new_i)
                except Mix.DoesNotExist:
                    print('This image is not used', similar + '.jpg')
