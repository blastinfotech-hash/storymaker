from django.core.management.base import BaseCommand, CommandError

from news.models import NewsSource
from news.services import import_active_sources, import_source_articles


class Command(BaseCommand):
    help = "Importa artigos a partir dos feeds RSS cadastrados."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Nome exato da fonte RSS a importar")
        parser.add_argument("--limit", type=int, default=20, help="Limite de entradas por feed")

    def handle(self, *args, **options):
        source_name = options["source"]
        limit = options["limit"]

        try:
            if source_name:
                source = NewsSource.objects.get(name=source_name)
                results = [import_source_articles(source=source, limit=limit)]
            else:
                results = import_active_sources(limit=limit)
        except NewsSource.DoesNotExist as exc:
            raise CommandError(f"Fonte RSS nao encontrada: {source_name}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        for result in results:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{result.source.name}: {result.created} criados, {result.updated} atualizados, {result.skipped} ignorados"
                )
            )
