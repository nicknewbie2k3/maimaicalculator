import json
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from .models import OldSong, NewSong, MaimaiSong

def parse_decimal(val):
    try:
        return Decimal(val)
    except (InvalidOperation, TypeError, ValueError):
        return None

def calculator_list(request):
    if request.method == 'POST':
        song_name = request.POST.get('song_name')
        difficulty_type = request.POST.get('difficulty_type')
        achievement = request.POST.get('achievement')
        achievement = Decimal(achievement)

        # Cap achievement at 100.5 for calculation only
        achievement_for_calc = achievement
        if achievement_for_calc > Decimal('100.5'):
            achievement_for_calc = Decimal('100.5')

        # Get chart difficulty and version from MaimaiSong
        song = MaimaiSong.objects.filter(title=song_name).first()
        chart_difficulty = None
        version = None
        if song:
            version = song.version
            if difficulty_type == "Basic":
                chart_difficulty = song.lev_bas
            elif difficulty_type == "Advanced":
                chart_difficulty = song.lev_adv
            elif difficulty_type == "Expert":
                chart_difficulty = song.lev_exp
            elif difficulty_type == "Master":
                chart_difficulty = song.lev_mas
            elif difficulty_type == "Re:Master":
                chart_difficulty = song.lev_remas

        # If not found, set to 0
        if not chart_difficulty:
            chart_difficulty = Decimal('0')

        # Determine rank based on achievement
        rank = ""
        if Decimal('60') <= achievement < Decimal('70'):
            rank = 'B'
        elif Decimal('70') <= achievement < Decimal('75'):
            rank = '2B'
        elif Decimal('75') <= achievement < Decimal('80'):
            rank = '3B'
        elif Decimal('80') <= achievement < Decimal('90'):
            rank = 'A'
        elif Decimal('90') <= achievement < Decimal('94'):
            rank = '2A'
        elif Decimal('94') <= achievement < Decimal('97'):
            rank = '3A'
        elif Decimal('97') <= achievement < Decimal('98'):
            rank = 'S'
        elif Decimal('98') <= achievement < Decimal('99'):
            rank = 'S+'
        elif Decimal('99') <= achievement < Decimal('99.5'):
            rank = '2S'
        elif Decimal('99.5') <= achievement < Decimal('100'):
            rank = '2S+'
        elif Decimal('100') <= achievement < Decimal('100.5'):
            rank = '3S'
        elif achievement >= Decimal('100.5'):
            rank = '3S+'
        else:
            rank = 'B'

        # Coefficient table
        coefficients = {
            'B': Decimal('9.6'),
            '2B': Decimal('11.2'),
            '3B': Decimal('12'),
            'A': Decimal('13.6'),
            '2A': Decimal('15.2'),
            '3A': Decimal('16.8'),
            'S': Decimal('20.0'),
            'S+': Decimal('20.3'),
            '2S': Decimal('20.8'),
            '2S+': Decimal('21.1'),
            '3S': Decimal('21.6'),
            '3S+': Decimal('22.4'),
        }
        coefficient = coefficients.get(rank, Decimal('0'))
        calculated_rating = (chart_difficulty * coefficient * achievement_for_calc / 100).to_integral_value(rounding=ROUND_DOWN)

        filter_kwargs = {
            'song_name': song_name,
            'chart_difficulty': chart_difficulty,
            'difficulty_type': difficulty_type,  # Add difficulty_type to filter and create
        }
        if version == "PRiSM PLUS":
            existing = NewSong.objects.filter(**filter_kwargs).first()
            if existing:
                if achievement > existing.achievement:
                    existing.delete()
                    NewSong.objects.create(
                        song_name=song_name,
                        rank=rank,
                        achievement=achievement,
                        chart_difficulty=chart_difficulty,
                        calculated_rating=calculated_rating,
                        difficulty_type=difficulty_type
                    )
                # else: do not add
            else:
                NewSong.objects.create(
                    song_name=song_name,
                    rank=rank,
                    achievement=achievement,
                    chart_difficulty=chart_difficulty,
                    calculated_rating=calculated_rating,
                    difficulty_type=difficulty_type
                )
        else:
            existing = OldSong.objects.filter(**filter_kwargs).first()
            if existing:
                if achievement > existing.achievement:
                    existing.delete()
                    OldSong.objects.create(
                        song_name=song_name,
                        rank=rank,
                        achievement=achievement,
                        chart_difficulty=chart_difficulty,
                        calculated_rating=calculated_rating,
                        difficulty_type=difficulty_type
                    )
                # else: do not add
            else:
                OldSong.objects.create(
                    song_name=song_name,
                    rank=rank,
                    achievement=achievement,
                    chart_difficulty=chart_difficulty,
                    calculated_rating=calculated_rating,
                    difficulty_type=difficulty_type
                )
        return redirect('calculator_list')

    # Prepare old and new songs
    old_songs = list(OldSong.objects.all().order_by('-calculated_rating')[:35])
    while len(old_songs) < 35:
        old_songs.append(None)
    new_songs = list(NewSong.objects.all().order_by('-calculated_rating')[:15])
    while len(new_songs) < 15:
        new_songs.append(None)

    # Combine old and new songs for a 5x10 grid (50 cells)
    all_songs = list(OldSong.objects.all().order_by('-calculated_rating')) + \
                list(NewSong.objects.all().order_by('-calculated_rating'))
    all_songs = all_songs[:50]
    while len(all_songs) < 50:
        all_songs.append(None)
    merged_grid = [all_songs[i*5:(i+1)*5] for i in range(10)]  # 10 rows, 5 columns

    # Purge lowest elements if limits exceeded
    old_count = OldSong.objects.count()
    new_count = NewSong.objects.count()
    if old_count > 35:
        to_delete = OldSong.objects.all().order_by('calculated_rating')[:old_count-35]
        for obj in to_delete:
            obj.delete()
    if new_count > 15:
        to_delete = NewSong.objects.all().order_by('calculated_rating')[:new_count-15]
        for obj in to_delete:
            obj.delete()
    # Calculate total ratings
    old_total_rating = sum(song.calculated_rating for song in old_songs if song)
    new_total_rating = sum(song.calculated_rating for song in new_songs if song)
    total_rating = old_total_rating + new_total_rating
    total_count = sum(1 for song in old_songs if song) + sum(1 for song in new_songs if song)
    total_average_rating = (total_rating / total_count) if total_count else 0
    all_song_names = MaimaiSong.objects.values_list('title', flat=True).distinct()
    maimai_songs = MaimaiSong.objects.all()
    maimai_songs_dict = {song.title: song for song in maimai_songs}
    return render(request, "main/calculator_list.html", {
        "old_songs": old_songs,
        "new_songs": new_songs,
        "merged_grid": merged_grid,  # <-- merged 10x5 grid
        "total_rating": total_rating,
        "old_total_rating": old_total_rating,
        "new_total_rating": new_total_rating,
        "total_average_rating": total_average_rating,
        "all_song_names": all_song_names,
        "maimai_songs_dict": maimai_songs_dict,
    })

def database_upload(request):
    message = ""
    if request.method == "POST" and request.FILES.get("json_file"):
        json_file = request.FILES["json_file"]
        try:
            data = json.load(json_file)
            uploaded_titles = set()
            for entry in data:
                title = entry.get('title', '').strip()
                if not title:
                    continue
                uploaded_titles.add(title)
                defaults = {
                    'title_kana': entry.get('title_kana'),
                    'artist': entry.get('artist'),
                    'catcode': entry.get('catcode'),
                    'image_url': entry.get('image_url'),
                    'release': entry.get('release'),
                    'lev_bas': parse_decimal(entry.get('lev_bas')),
                    'lev_adv': parse_decimal(entry.get('lev_adv')),
                    'lev_exp': parse_decimal(entry.get('lev_exp')),
                    'lev_mas': parse_decimal(entry.get('lev_mas')),
                    'lev_remas': parse_decimal(entry.get('lev_remas')),
                    'sort': entry.get('sort'),
                    'version': entry.get('version'),
                    'chart_type': entry.get('chart_type'),
                }
                obj, created = MaimaiSong.objects.get_or_create(title=title, defaults=defaults)
                if not created:
                    # Only update if any field is different
                    changed = False
                    for field, value in defaults.items():
                        if getattr(obj, field) != value:
                            setattr(obj, field, value)
                            changed = True
                    if changed:
                        obj.save()
            # Remove songs not in the uploaded file
            MaimaiSong.objects.exclude(title__in=uploaded_titles).delete()
            message = f"Upload successful. {len(uploaded_titles)} songs now in the database."
        except Exception as e:
            message = f"Error processing file: {e}"
    return render(request, "main/databaseUpload.html", {"message": message})

def chart_database(request):
    songs_qs = MaimaiSong.objects.all()

    # Filtering
    title = request.GET.get('title', '').strip()
    version = request.GET.get('version', '').strip()
    artist = request.GET.get('artist', '').strip()
    catcode = request.GET.get('catcode', '').strip()
    chart_type = request.GET.get('chart_type', '').strip()
    difficulty = request.GET.get('difficulty', '').strip()

    if title:
        songs_qs = songs_qs.filter(title__icontains=title)
    if version:
        songs_qs = songs_qs.filter(version__icontains=version)
    if artist:
        songs_qs = songs_qs.filter(artist__icontains=artist)
    if catcode:
        songs_qs = songs_qs.filter(catcode=catcode)
    if chart_type:
        songs_qs = songs_qs.filter(chart_type=chart_type)
    if difficulty:
        # Only show songs where the selected difficulty is not null/blank
        field_map = {
            "Basic": "lev_bas",
            "Advanced": "lev_adv",
            "Expert": "lev_exp",
            "Master": "lev_mas",
            "Re:Master": "lev_remas",
        }
        field = field_map.get(difficulty)
        if field:
            filter_kwargs = {f"{field}__isnull": False}
            songs_qs = songs_qs.filter(**filter_kwargs).exclude(**{field: ""})

    # Pagination
    paginator = Paginator(songs_qs, 30)
    page_number = request.GET.get('page')
    songs = paginator.get_page(page_number)

    # Unique values for dropdowns
    filter_titles = MaimaiSong.objects.values_list('title', flat=True).distinct().order_by('title')
    filter_versions = MaimaiSong.objects.values_list('version', flat=True).distinct().order_by('version')
    filter_artists = MaimaiSong.objects.values_list('artist', flat=True).distinct().order_by('artist')
    # Catcode: fixed 7 options
    filter_catcodes = [
        "POPS＆ANIME",
        "niconico＆VOCALOID™",
        "東方Project",
        "GAME＆VARIETY",
        "maimai",
        "オンゲキ＆CHUNITHM",
        "宴会場"
    ]

    return render(request, "main/chart_database.html", {
        "songs": songs,
        "filter_titles": filter_titles,
        "filter_versions": filter_versions,
        "filter_artists": filter_artists,
        "filter_catcodes": filter_catcodes,
    })
