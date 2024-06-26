from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import TemplateView
from django.http import Http404
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import F
from django.conf import settings
from django.utils.crypto import get_random_string
from django.urls import reverse_lazy, reverse
from invitations.utils import get_invitation_model
from .models import Show, CurrentlyWatching, Season, UserEx
from .forms import NewLogForm
from .utils import create_watching_groups
# Create your views here.
class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        if user.is_authenticated:
            current = [x for x in user.currentlywatching_set.order_by('-date') if x.episode < x.season.episodes]
            context['current'] = create_watching_groups(current)

            watched_shows = [x for x in user.currentlywatching_set.order_by('-date') if x.episode >= x.season.episodes]
            context['last_watched_shows'] = create_watching_groups(watched_shows, max_shows_displayed=3)[:3]

        context["last_added_shows"] = Show.objects.order_by('creation_date')[::-1][:3]
        return context

class AboutView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['user_count'] = User.objects.all().count()
        context['show_count'] = Show.objects.all().count()
        context['log_count'] = CurrentlyWatching.objects.all().count()

        return context

class ShowListView(ListView):
    model = Show
    template_name = "shows.html"
    context_object_name = "shows"

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get('q', '')

        queryset = queryset.order_by(F('enddate').asc(nulls_last=True), '-startdate')[::-1]

        result = [x for x in queryset if search_query.lower() in x.name.lower()]

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        search_query = self.request.GET.get('q', '')

        context['search_query'] = search_query

        return context

class ShowDetailView(DetailView):
    model = Show
    template_name = "show_detail.html"
    context_object_name = "show"
    slug_field = 'abbreviation'
    slug_url_kwarg = 'abbreviation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['seasons'] = context['show'].season_set.order_by('startdate')
        context['seasonplural'] = len(context['seasons']) > 1

        user = self.request.user
        if user.is_authenticated:
            currentlywatching = user.currentlywatching_set.filter(season__in=context['seasons']).order_by('season__startdate')

            context['progress_watching'] = [x for x in currentlywatching if x.episode < x.season.episodes]
            context['progress_watched'] = [x for x in currentlywatching if x.episode >= x.season.episodes]
            context['show_progress'] = len(currentlywatching) > 0

            context['is_watchlist'] = context['show'] in user.userex.watchlist.all()

        return context

    def post(self, request, *args, **kwargs):
        show_req = request.POST.get('show')

        show = get_object_or_404(Show, abbreviation=show_req)
        userex = request.user.userex

        if show in userex.watchlist.all():
            userex.watchlist.remove(show)
        else:
            userex.watchlist.add(show)

        userex.save()

        return redirect("watchlist")

class WatchListView(LoginRequiredMixin, TemplateView):
    template_name = "watchlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        context['watchlist'] = user.userex.watchlist.all()

        return context

class WatchingCreateView(LoginRequiredMixin, CreateView):
    model = CurrentlyWatching
    template_name = "watching_create.html"
    form_class = NewLogForm
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "new"

        user = self.request.user
        show = self.kwargs.pop('show', None)
        logged_seasons = user.currentlywatching_set.filter(season__show=show)
        context['logged_seasons'] = [x.season for x in logged_seasons]
        context['update_date'] = True

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        slug = self.kwargs.pop('abbreviation', None)
        show = get_object_or_404(Show, abbreviation=slug)
        kwargs['show'] = show
        self.kwargs['show'] = show

        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class WatchingUpdateView(LoginRequiredMixin, UpdateView):
    model = CurrentlyWatching
    template_name = "watching_create.html"
    context_object_name = "watching"
    fields = ["date", "episode", "rating", "rewatch"]
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "update"
        context['update_date'] = context['form'].instance.episode < context['watching'].season.episodes

        return context

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.author == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.author == self.request.user:
            raise Http404
        else:
            return super().form_valid(form)

class WatchingDeleteView(LoginRequiredMixin, DeleteView):
    model = CurrentlyWatching
    template_name = "object_delete.html"
    context_object_name = "watching"
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['flavor_string'] = f"{self.request.user.username}'s log for {context['watching'].season.show.name} - Season {context['watching'].season.name}"

        return context

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.author == self.request.user:
            raise Http404
        return obj

    def form_valid(self, form, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.author == self.request.user:
            raise Http404
        else:
            return super().form_valid(form)

class SeasonCreateView(LoginRequiredMixin, CreateView):
    model = Season
    template_name = "season_create.html"
    fields = ["name", "episodes", "startdate"]
    success_url = reverse_lazy("shows")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "new"

        return context

    def get_form(self):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_form()

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            slug = self.kwargs.pop('abbreviation', None)
            show = get_object_or_404(Show, abbreviation=slug)
            form.instance.show = show
            return super().form_valid(form)

class SeasonUpdateView(LoginRequiredMixin, UpdateView):
    model = Season
    template_name = "season_create.html"
    fields = ["name", "episodes", "startdate"]
    context_object_name = "season"
    success_url = reverse_lazy("shows")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "update"

        return context

    def get_object(self, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_object(*args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().form_valid(form)

class SeasonDeleteView(LoginRequiredMixin, DeleteView):
    model = Season
    template_name = "object_delete.html"
    context_object_name = "season"
    success_url = reverse_lazy("shows")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['flavor_string'] = f"{context['season'].show.name} - Season {context['season'].name} ({context['season'].episodes})"

        return context

    def get_object(self, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_object(*args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().form_valid(form)

class ShowCreateView(LoginRequiredMixin, CreateView):
    model = Show
    template_name = "show_create.html"
    fields = ["name", "startdate", "enddate", "boxart", "abbreviation"]
    success_url = reverse_lazy("shows")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "new"

        return context

    def get_form(self):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_form()

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().form_valid(form)

class ShowUpdateView(LoginRequiredMixin, UpdateView):
    model = Show
    template_name = "show_create.html"
    fields = ["name", "startdate", "enddate", "boxart", "abbreviation"]
    context_object_name = "show"
    success_url = reverse_lazy("shows")
    slug_field = 'abbreviation'
    slug_url_kwarg = 'abbreviation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['type'] = "update"

        return context

    def get_object(self, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_object(*args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().form_valid(form)

class ShowDeleteView(LoginRequiredMixin, DeleteView):
    model = Show
    template_name = "object_delete.html"
    context_object_name = "show"
    success_url = reverse_lazy("shows")
    slug_field = 'abbreviation'
    slug_url_kwarg = 'abbreviation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['flavor_string'] = f"{context['show'].name}"

        return context

    def get_object(self, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().get_object(*args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        if not self.request.user.userex.isEditor:
            raise Http404
        else:
            return super().form_valid(form)

class InviteCreateView(LoginRequiredMixin, TemplateView):
    template_name = "create_invite.html"

    def get(self, request, *args, **kwargs):
        if not request.user.userex.isEditor:
            raise Http404
        else:
            return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.userex.isEditor:
            raise Http404

        email_req = request.POST.get('email')
        if not email_req:
            email_req = f'{get_random_string(10).lower()}@example.com'

        invitation = get_invitation_model()
        invite = invitation.create(email_req, inviter=request.user)
        invite.send_invitation(request)

        url_name = "invitations:accept-invite"

        try:
            url_name = settings.INVITATIONS_CONFIRMATION_URL_NAME
        except AttributeError:
            pass

        invite_url = reverse(url_name, args=[invite.key])
        invite_url = request.build_absolute_uri(invite_url)

        context = self.get_context_data(**kwargs)
        context['invite_url'] = invite_url

        return self.render_to_response(context=context)

class ProfileView(DetailView):
    model = User
    template_name = "profile.html"
    context_object_name = 'profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = context['profile']

        if not user.userex.isPublic:
            if not self.request.user.is_authenticated or self.request.user != user:
                raise Http404

        current = [x for x in user.currentlywatching_set.order_by('-date') if x.episode < x.season.episodes]
        context['current'] = create_watching_groups(current)

        watched_shows = [x for x in user.currentlywatching_set.order_by('-date') if x.episode >= x.season.episodes]
        context['last_watched_shows'] = create_watching_groups(watched_shows)

        context['stats'] = f"{len(context['last_watched_shows'])} shows, {len(watched_shows)} seasons"

        return context

class EditProfileView(LoginRequiredMixin, UpdateView):
    model = UserEx
    template_name = "edit_profile.html"
    context_object_name = 'profile'
    fields = ["displayname", "isPublic"]
    success_url = reverse_lazy("home")

    def get_object(self, *args, **kwargs):
        return self.request.user.userex

    def form_valid(self, form, *args, **kwargs):
        if form.instance.user != self.request.user:
            raise Http404
        else:
            return super().form_valid(form)
