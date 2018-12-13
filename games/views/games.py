"""API views module"""
from __future__ import absolute_import

from rest_framework import filters, generics, permissions
from rest_framework.response import Response

from games import models, serializers


class GameListView(generics.GenericAPIView):
    """CBV for games list"""
    filter_backends = (filters.SearchFilter, )
    search_fields = ('slug', 'name')

    def get_queryset(self):
        """Return the query set for the game list

        This view can be queried by the client to get all lutris games
        available based on a series of criteria such as a list of slugs or GOG
        ids.
        """

        base_query = models.Game.objects

        # Easter egg: Return a random game
        if 'random' in self.request.GET:
            return [base_query.get_random(self.request.GET['random'])]

        # A list of slugs is sent from the client, we match them against Lutris
        # games.
        if 'games' in self.request.GET:
            game_slugs = self.request.GET.getlist('games')
        elif 'games' in self.request.data:
            game_slugs = self.request.data.get('games')
        else:
            game_slugs = None
        if game_slugs:
            return base_query.filter(change_for__isnull=True, slug__in=game_slugs)

        if 'gogid' in self.request.data:
            gog_ids = self.request.data.get('gogid')
            return base_query.filter(change_for__isnull=True, gogid__in=gog_ids)

        return base_query.filter(change_for__isnull=True)

    def get_serializer_class(self):
        """Return the appropriate serializer

        Adding ?installer=1 to the url adds the installers to the games
        """
        if self.request.GET.get('installers') == '1':
            return serializers.GameInstallersSerializer
        return serializers.GameSerializer

    def get(self, request):
        """GET request"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """POST request"""
        # Using POST instead of GET is a violation of API rules but it's the
        # only way to send a huge payload to the server. GET querystrings only
        # support a limited number of characters (depending on the web server or
        # the browser used) whereas POST request do not have this limitation.
        return self.get(request)


class GameLibraryView(generics.RetrieveAPIView):
    serializer_class = serializers.GameLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username):
        try:
            library = models.GameLibrary.objects.get(user__username=username)
        except models.GameLibrary.DoesNotExist:
            return Response(status=404)
        serializer = serializers.GameLibrarySerializer(library)
        return Response(serializer.data)


class GameDetailView(generics.RetrieveAPIView):
    serializer_class = serializers.GameSerializer
    lookup_field = 'slug'
    queryset = models.Game.objects.filter(change_for__isnull=True)


class GameInstallersView(generics.RetrieveAPIView):
    serializer_class = serializers.GameInstallersSerializer
    lookup_field = 'slug'
    queryset = models.Game.objects.filter(change_for__isnull=True)
