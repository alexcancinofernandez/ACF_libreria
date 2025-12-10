
from django.core.management.base import BaseCommand
from app_tienda.models import Libro, Categoria
import random

class Command(BaseCommand):
    help = 'Crea 10 registros de libros con datos ficticios.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Creando registros de libros...")

        # Nombres y datos ficticios
        titulos_autores = [
            ("El Poder de la Mente Subconsciente", "Joseph Murphy"),
            ("Trances Terapéuticos", "Stephen G. Gilligan"),
            ("La Biblia", "Varios"),
            ("El Corán", "Varios"),
            ("Piense y Hágase Rico", "Napoleón Hill"),
            ("Los 7 Hábitos de la Gente Altamente Efectiva", "Stephen Covey"),
            ("El Arte de la Guerra", "Sun Tzu"),
            ("Las 48 Leyes del Poder", "Robert Greene"),
            ("Meditaciones", "Marco Aurelio"),
            ("El Kybalión", "Tres Iniciados")
        ]

        # Asegúrate de que las categorías existan
        cat_hipnosis, _ = Categoria.objects.get_or_create(nombre='Hipnosis', defaults={'descripcion': 'Libros sobre hipnosis.'})
        cat_religion, _ = Categoria.objects.get_or_create(nombre='Religión', defaults={'descripcion': 'Libros sobre religión.'})
        cat_desarrollo, _ = Categoria.objects.get_or_create(nombre='Desarrollo Personal', defaults={'descripcion': 'Libros de autoayuda.'})
        cat_poder, _ = Categoria.objects.get_or_create(nombre='Poder', defaults={'descripcion': 'Libros sobre poder e influencia.'})

        # Asignación de categorías
        libro_categorias = {
            "El Poder de la Mente Subconsciente": cat_hipnosis,
            "Trances Terapéuticos": cat_hipnosis,
            "La Biblia": cat_religion,
            "El Corán": cat_religion,
            "Piense y Hágase Rico": cat_desarrollo,
            "Los 7 Hábitos de la Gente Altamente Efectiva": cat_desarrollo,
            "El Arte de la Guerra": cat_poder,
            "Las 48 Leyes del Poder": cat_poder,
            "Meditaciones": cat_desarrollo,
            "El Kybalión": cat_hipnosis
        }

        for titulo, autor in titulos_autores:
            categoria = libro_categorias[titulo]
            
            Libro.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'autor': autor,
                    'categoria': categoria,
                    'descripcion': f'Descripción detallada de {titulo}.',
                    'descripcion_corta': f'Un libro sobre {categoria.nombre}.',
                    'precio': round(random.uniform(9.99, 29.99), 2),
                    'formato': random.choice(['pdf', 'epub', 'mobi']),
                    'archivo_digital': 'libros_digitales/default.pdf', # Archivo de ejemplo
                    'portada': 'portadas/default.jpg', # Portada de ejemplo
                    'paginas': random.randint(150, 500),
                    'isbn': f'978-0-00-{random.randint(100000, 999999)}-{random.randint(0,9)}'
                }
            )

        self.stdout.write(self.style.SUCCESS("¡10 libros creados exitosamente!"))
