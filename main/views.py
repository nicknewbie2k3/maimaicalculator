import json
import zlib
import gzip
import bz2
import re
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from datetime import datetime
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib import messages
from .models import OldSong, NewSong, MaimaiSong
from inertia import inertia

def parse_decimal(val):
    try:
        return Decimal(val)
    except (InvalidOperation, TypeError, ValueError):
        return None


def find_maimai_song_by_title(title):
    """Lookup helper that tries exact title, tag-normalized variants, aliases, and partial matches.

    Enhanced normalization: converts fullwidth punctuation to ASCII, normalizes
    curly quotes/apostrophes, collapses whitespace, and handles common
    'feat.' punctuation differences. Also supports a small special-case map for
    problematic cache titles that don't match DB spelling/spacing.
    """
    if not title:
        return None

    def _normalize_for_lookup(s: str) -> str:
        s = s.strip()
        # Fullwidth and punctuation normalization
        replacements = {
            '～': '~', '〜': '~', '（': '(', '）': ')', '【': '[', '】': ']', '　': ' ',
            '＃': '#', '＆': '&', '：': ':', '’': "'", '‘': "'", '“': '"', '”': '"',
            '—': '-', '–': '-', '。': '.', '、': ',', '．': '.', '：': ':', '･': '･'
        }
        for k, v in replacements.items():
            s = s.replace(k, v)

        # Normalize common punctuation variants and spacing
        s = s.replace('feat.', 'feat').replace('Feat.', 'Feat')
        s = s.replace('. ', '.').replace(' .', '.')
        # Normalize curly quotes to ASCII
        s = s.replace('“', '"').replace('”', '"')
        s = s.replace("’", "'").replace("‘", "'")

        # Collapse whitespace
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # Small special-case title map (normalized_key -> canonical DB title)
    special_map = {
        _normalize_for_lookup('VIIIBit Explorer (ST)').lower(): 'VIIIbit Explorer [STD]',
        _normalize_for_lookup('Bad Apple!! feat nomico').lower(): 'Bad Apple!! feat.nomico [STD]',
        _normalize_for_lookup('Sunday Night feat. Kanata.N').lower(): 'Sunday Night feat Kanata.N [DX]',
        _normalize_for_lookup('“411Ψ892”').lower(): '"411Ψ892" [DX]',
        _normalize_for_lookup("World’s end loneliness").lower(): "World's end loneliness [DX]",
        _normalize_for_lookup('＃狂った民族２ PRAVARGYAZOOQA').lower(): '#狂った民族２ PRAVARGYAZOOQA [DX]',
        _normalize_for_lookup('Help me, ERINNNNNN!! (Band ver.)').lower(): 'Help me, ERINNNNNN!!（Band ver.） [STD]',
        _normalize_for_lookup("Don't Fight The Music").lower(): "Don't Fight The Music [DX]",
        _normalize_for_lookup('おべんきょうたいむ').lower(): 'おべんきょうたいむ [DX]',
        # Added mappings for recently reported missing/oddly-formatted titles
        _normalize_for_lookup('セイクリッド　ルイン').lower(): 'セイクリッド　ルイン [STD]',
        _normalize_for_lookup('大輪の魂 (feat. AO, 司芭扶)').lower(): '大輪の魂 (feat. AO, 司芭扶) [DX]',
        _normalize_for_lookup('ここからはじまるプロローグ。').lower(): 'ここからはじまるプロローグ。 [DX]',
        _normalize_for_lookup('Tic Tac DREAMIN’').lower(): 'Tic Tac DREAMIN’ [STD]',
        _normalize_for_lookup('メイトなやつら（FEAT. 天開司, 佐藤ホームズ, あっくん大魔王 & 歌衣メイカ)').lower(): 'メイトなやつら（FEAT. 天開司, 佐藤ホームズ, あっくん大魔王 & 歌衣メイカ） [DX]',
        _normalize_for_lookup('Make Up Your World feat. キョンシーのCiちゃん & らっぷびと').lower(): 'Make Up Your World feat. キョンシーのCiちゃん & らっぷびと [DX]',
        _normalize_for_lookup('宛城、炎上！！').lower(): '宛城、炎上！！ [DX]',
        _normalize_for_lookup('ネコ日和。[DX]').lower(): 'ネコ日和。 [DX]',
        _normalize_for_lookup('ぼくたちいつでも　しゅわっしゅわ！').lower(): 'ぼくたちいつでも　しゅわっしゅわ！ [DX]',
        _normalize_for_lookup('【東方ニコカラ】秘神マターラ feat.魂音泉【IOSYS】').lower(): '【東方ニコカラ】秘神マターラ feat.魂音泉【IOSYS】 [STD]',
        _normalize_for_lookup('オーディエンスを沸かす程度の能力 feat.タイツォン').lower(): 'オーディエンスを沸かす程度の能力 feat.タイツォン [STD]',
        _normalize_for_lookup('Bad Apple!! feat.nomico (Tetsuya Komuro Remix)').lower(): 'Bad Apple!! feat.nomico (Tetsuya Komuro Remix) [DX]',
    }

    # Additional mappings discovered by cache vs DB analysis
    # (normalized cache title -> canonical DB title)
    special_map.update({
        _normalize_for_lookup('ラストピースに祝福と栄光を').lower(): 'ラストピースに祝福と栄光を [DX]',
        _normalize_for_lookup('ジングルベル[DX]').lower(): 'ジングルベル [DX]',
        _normalize_for_lookup('君だったから').lower(): '君だったから [DX]',
        _normalize_for_lookup('Ievan Polkka').lower(): 'Ievan Polkka [STD]',
        _normalize_for_lookup('ナイト・オブ・ナイツ[DX]').lower(): 'ナイト・オブ・ナイツ [DX]',
        _normalize_for_lookup('響縁[DX]').lower(): '響縁 [DX]',
        _normalize_for_lookup('JINGLE DEATH').lower(): 'JINGLE DEATH [DX]',
        _normalize_for_lookup('鬼女紅妖').lower(): '鬼女紅妖 [DX]',
        _normalize_for_lookup('ソテリア').lower(): 'ソテリア [DX]',
        _normalize_for_lookup('Sky Trails').lower(): 'Sky Trails [DX]',
        _normalize_for_lookup('ミクマリ').lower(): 'ミクマリ [DX]',
        _normalize_for_lookup('Treasure Chest Expedition').lower(): 'Treasure Chest Expedition [DX]',
    })

    normalized_input = _normalize_for_lookup(title)
    # If a special-case mapping exists, use it as the raw title to query
    if normalized_input.lower() in special_map:
        t_raw = special_map[normalized_input.lower()]
    else:
        t_raw = title.strip()

    # Try exact as-provided or mapped title first
    try:
        exact = MaimaiSong.objects.filter(title=t_raw).first()
        if exact:
            return exact
    except Exception:
        pass

    # Use normalized form for candidate generation
    t = normalized_input.replace('～', '~').replace('〜', '~')

    # Remove common trailing tags if present to get base name
    base = t
    for tag in (' [DX]', '[DX]', ' [ST]', '[ST]', ' [STD]', '[STD]'):
        if base.endswith(tag):
            base = base[:-len(tag)].strip()

    # Generate tilde variants for the base (ASCII, fullwidth, wave dash)
    tilde_variants = ['~', '～', '〜']
    base_variants = set()
    canonical_base = base.replace('～', '~').replace('〜', '~')
    for tv in tilde_variants:
        base_variants.add(canonical_base.replace('~', tv))

    # Determine requested tag from input and build candidate titles
    requested_tag = None
    if re.search(r'\[\s*DX\s*\]$', t, re.IGNORECASE):
        requested_tag = 'DX'
    elif re.search(r'\[\s*ST\s*\]$', t, re.IGNORECASE) or re.search(r'\[\s*STD\s*\]$', t, re.IGNORECASE):
        requested_tag = 'STD'

    tag_order = ['STD', 'ST', 'DX']
    if requested_tag == 'DX':
        tag_order = ['DX', 'STD', 'ST']
    elif requested_tag == 'STD':
        tag_order = ['STD', 'ST', 'DX']

    # Build candidate titles from base variants with/without tags
    candidates = []
    for b in base_variants:
        for tag in tag_order:
            candidates.append(f"{b} [{tag}]")
            candidates.append(f"{b}[{tag}]")
        candidates.append(b)
    candidates.append(t)

    # Try exact candidate matches (case-sensitive then case-insensitive)
    for c in candidates:
        try:
            s = MaimaiSong.objects.filter(title=c).first()
            if s:
                return s
        except Exception:
            continue

    for c in candidates:
        try:
            s = MaimaiSong.objects.filter(title__iexact=c).first()
            if s:
                return s
        except Exception:
            continue

    # Alias match: compare normalized alias base to our canonical base
    canonical_base_lower = canonical_base.lower()
    songs_with_aliases = MaimaiSong.objects.filter(aliases__isnull=False)
    for s in songs_with_aliases:
        try:
            aliases_list = s.get_aliases_list()
        except Exception:
            aliases_list = []
        for alias in aliases_list:
            a = alias.strip()
            # Normalize alias text for comparison
            a = _normalize_for_lookup(a).replace('～', '~').replace('〜', '~')
            for tag in (' [DX]', '[DX]', ' [ST]', '[ST]', ' [STD]', '[STD]'):
                if a.endswith(tag):
                    a = a[:-len(tag)].strip()
            if a.lower() == canonical_base_lower:
                return s

    # Final fallback: partial match in title using canonical base variants
    # Only accept partial matches when the canonical base is reasonably long
    # and yields a unique DB result to avoid incorrect cross-matches.
    if len(canonical_base) >= 6:
        for b in base_variants:
            try:
                qs = MaimaiSong.objects.filter(title__icontains=b)
                if qs.count() == 1:
                    return qs.first()
            except Exception:
                continue

    return None

@inertia('Index')
def calculator_list(request):
    if request.method == 'POST':
        try:
            song_name = request.POST.get('song_name')
            difficulty_type = request.POST.get('difficulty_type')
            achievement = request.POST.get('achievement')
            
            # Validate required fields
            if not song_name or not difficulty_type or not achievement:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
            
            # Convert achievement to Decimal with error handling
            try:
                achievement = Decimal(achievement)
            except (InvalidOperation, ValueError):
                return JsonResponse({'status': 'error', 'message': 'Invalid achievement value'})

            # Cap achievement at 100.5 for calculation only
            achievement_for_calc = achievement
            if achievement_for_calc > Decimal('100.5'):
                achievement_for_calc = Decimal('100.5')

            # Get chart difficulty and version from MaimaiSong (use robust lookup)
            song = find_maimai_song_by_title(song_name)
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

            # Optional: accept clear type from POST (numeric 3/4/5/6 or string 'AP'/'AP+')
            raw_clear_post = request.POST.get('clear_type') or request.POST.get('clearType') or request.POST.get('clear')
            try:
                raw_clear_int = int(raw_clear_post) if raw_clear_post is not None else None
            except Exception:
                raw_clear_int = None

            # Apply +1 bonus for AP/AP+ if indicated
            try:
                rating_int = int(calculated_rating)
            except Exception:
                rating_int = int(calculated_rating) if calculated_rating else 0

            if raw_clear_int in (5, 6) or (isinstance(raw_clear_post, str) and raw_clear_post.strip().upper() in ('AP', 'AP+')):
                rating_int += 1

            # Return song data as JSON for localStorage handling
            song_data = {
                'song_name': song_name,
                'difficulty_type': difficulty_type,
                'rank': rank,
                'achievement': float(achievement),
                'chart_difficulty': float(chart_difficulty),
                'calculated_rating': rating_int,
                'version': version
            }
            
            return JsonResponse({'status': 'success', 'song_data': song_data})
            
        except Exception as e:
            # Log the error for debugging
            print(f"Error in calculator_list POST: {e}")
            return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'})

    # Return empty data - frontend will populate from localStorage
    all_song_names = list(MaimaiSong.objects.values_list('title', flat=True).distinct())
    maimai_songs = MaimaiSong.objects.all()
    maimai_songs_dict = {song.title: song for song in maimai_songs}
    
    # Add aliases to song names for search
    alias_to_title_map = {}
    all_songs = MaimaiSong.objects.exclude(aliases__isnull=True).exclude(aliases__exact='')
    for song in all_songs:
        aliases_list = song.get_aliases_list()
        for alias in aliases_list:
            if alias.strip():  # Only add non-empty aliases
                alias_to_title_map[alias] = song.title
                # Add original title to list if not already there
                if song.title not in all_song_names:
                    all_song_names.append(song.title)
    
    # Sort the song names
    all_song_names = sorted(all_song_names)
    
    maimai_songs_data = {
        title: {
            'version': song.version or '',
            'chart_type': song.chart_type or '',
            'image_url': song.image_url or '',
        }
        for title, song in maimai_songs_dict.items()
    }
    return {
        'allSongNames': all_song_names,
        'maimaiSongsDict': maimai_songs_data,
        'aliasToTitleMap': alias_to_title_map,
    }

@inertia('DatabaseUpload')
def database_upload(request):
    if request.method == "POST" and request.FILES.get("json_file"):
        message = ""
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
                
                # Handle aliases separately (whether created or updated)
                # Always process aliases to ensure they're updated/cleared properly
                # Support both 'alias' and 'aliases' keys for flexibility
                aliases = entry.get('aliases', entry.get('alias', []))
                current_aliases = obj.get_aliases_list()
                
                # Update aliases if they're different
                if aliases != current_aliases:
                    obj.set_aliases_list(aliases)
                    obj.save()
            # Remove songs not in the uploaded file
            MaimaiSong.objects.exclude(title__in=uploaded_titles).delete()
            message = f"Upload successful. {len(uploaded_titles)} songs now in the database."
        except Exception as e:
            message = f"Error processing file: {e}"
        request.session['db_upload_message'] = message
        return redirect('database_upload')
    return {'message': request.session.pop('db_upload_message', '')}

def save_b50_data(request):
    """Export B50 data from localStorage as JSON file for download."""
    if request.method == 'POST':
        try:
            # Receive B50 data from frontend localStorage
            data = json.loads(request.body)
            old_songs = data.get('old_songs', [])
            new_songs = data.get('new_songs', [])
            
            # Validate that we have some data to export
            if not old_songs and not new_songs:
                return JsonResponse({'status': 'error', 'message': 'No B50 data to export. Add some songs first!'})
            
            # Ensure version information is included for all songs
            all_song_arrays = [old_songs, new_songs]
            for song_array in all_song_arrays:
                for song in song_array:
                    if 'version' not in song or not song['version']:
                        # Try to get version from database
                        try:
                            maimai_song = find_maimai_song_by_title(song.get('song_name', ''))
                            if maimai_song and maimai_song.version:
                                song['version'] = maimai_song.version
                            else:
                                # Set a default version if not found in database
                                # Assume old chart if unknown (safer default)
                                song['version'] = 'unknown'
                        except Exception as e:
                            # If database query fails, set default version
                            song['version'] = 'unknown'
            
            # Convert to JSON-serializable format
            b50_data = {
                'export_info': {
                    'version': '2.0',  # Updated version to reflect improved export
                    'export_date': '2026-04-08',
                    'total_songs': len(old_songs) + len(new_songs),
                    'note': 'Version information preserved for accurate re-import'
                },
                'old_songs': old_songs,
                'new_songs': new_songs
            }
            
            # Create JSON response for download
            response = HttpResponse(
                json.dumps(b50_data, indent=2),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = 'attachment; filename="maimai_b50_data.json"'
            return response
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data received from client.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error creating export file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

def load_b50_data(request):
    """Load B50 data from uploaded JSON file and return it for localStorage."""
    if request.method == 'POST' and request.FILES.get('b50_file'):
        try:
            json_file = request.FILES['b50_file']
            data = json.load(json_file)
            
            # Validate JSON structure
            if 'old_songs' not in data or 'new_songs' not in data:
                return JsonResponse({'status': 'error', 'message': 'Invalid file format. Missing old_songs or new_songs data.'})
            
            # Apply AP/AP+ bonus to any imported song entries where applicable.
            def _compute_rating_from_fields(song):
                try:
                    # Use chart_difficulty, achievement and rank to recompute rating
                    ach = Decimal(str(song.get('achievement', 0)))
                except Exception:
                    try:
                        ach = Decimal(str(float(song.get('achievement', 0))))
                    except Exception:
                        ach = Decimal('0')

                # Cap achievement for calculation
                achievement_for_calc = ach
                if achievement_for_calc > Decimal('100.5'):
                    achievement_for_calc = Decimal('100.5')

                try:
                    chart_d = Decimal(str(song.get('chart_difficulty', song.get('chartDifficulty', 0))))
                except Exception:
                    try:
                        chart_d = Decimal(str(float(song.get('chart_difficulty', 0))))
                    except Exception:
                        chart_d = Decimal('0')

                # Determine rank -> coefficient mapping (same as elsewhere)
                rank = (song.get('rank') or '').strip()
                rank_map = {
                    'B': Decimal('9.6'), '2B': Decimal('11.2'), '3B': Decimal('12'),
                    'A': Decimal('13.6'), '2A': Decimal('15.2'), '3A': Decimal('16.8'),
                    'S': Decimal('20.0'), 'S+': Decimal('20.3'), '2S': Decimal('20.8'),
                    '2S+': Decimal('21.1'), '3S': Decimal('21.6'), '3S+': Decimal('22.4')
                }
                coeff = rank_map.get(rank, Decimal('0'))
                try:
                    calc = (chart_d * coeff * achievement_for_calc / 100).to_integral_value(rounding=ROUND_DOWN)
                    return int(calc)
                except Exception:
                    try:
                        return int(chart_d * coeff * achievement_for_calc / 100)
                    except Exception:
                        return 0

            def _normalize_clear_val(song):
                # Look for numeric or textual clear markers in common places
                if isinstance(song.get('stats'), dict):
                    val = song['stats'].get('clearType')
                else:
                    val = song.get('clearType') or song.get('clear_type') or song.get('clear')
                try:
                    if val is None:
                        return None
                    return int(val)
                except Exception:
                    if isinstance(val, str):
                        v = val.strip().upper()
                        if v in ('AP', 'AP+'):
                            return 5
                        if v in ('FC', 'FC+'):
                            return 3
                    return None

            for list_key in ('old_songs', 'new_songs'):
                arr = data.get(list_key, [])
                if not isinstance(arr, list):
                    continue
                for song in arr:
                    try:
                        clear_val = _normalize_clear_val(song)
                        # Ensure calculated_rating is an int (or recompute if missing/invalid)
                        try:
                            cr = int(song.get('calculated_rating'))
                        except Exception:
                            cr = _compute_rating_from_fields(song)

                        # If AP/AP+ then add +1 bonus (avoid double-applying by checking a flag)
                        if clear_val in (5, 6) or (isinstance(song.get('clear_type'), str) and song.get('clear_type').upper() in ('AP', 'AP+')):
                            if not song.get('ap_bonus_applied'):
                                cr += 1
                                song['calculated_rating'] = cr
                                song['ap_bonus_applied'] = True
                        else:
                            # If calculated_rating missing, write computed value
                            if 'calculated_rating' not in song or song.get('calculated_rating') is None:
                                song['calculated_rating'] = cr
                    except Exception:
                        continue

            # Return the (possibly adjusted) data for frontend localStorage handling
            return JsonResponse({
                'status': 'success', 
                'message': 'B50 data loaded successfully!',
                'data': {
                    'old_songs': data.get('old_songs', []),
                    'new_songs': data.get('new_songs', [])
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON file format.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'No file uploaded or invalid request method.'})

def load_astro_cache_data(request):
    """Load and decompress astro cache data from uploaded compressed file."""
    if request.method == 'POST' and request.FILES.get('astro_cache_file'):
        try:
            cache_file = request.FILES['astro_cache_file']
            
            # Read the raw file content
            compressed_content = cache_file.read()
            
            # Try different decompression methods
            decompressed_content = None
            compression_method = None
            
            # First, try to parse as uncompressed JSON
            try:
                decompressed_text = compressed_content.decode('utf-8')
                json.loads(decompressed_text)  # Validate it's JSON
                compression_method = "uncompressed"
                decompressed_content = decompressed_text
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            
            # If not JSON, try different decompression methods
            if decompressed_content is None:
                compression_methods = [
                    ("gzip", lambda x: gzip.decompress(x)),
                    ("deflate", lambda x: zlib.decompress(x)),
                    ("deflate_raw", lambda x: zlib.decompress(x, -zlib.MAX_WBITS)),
                    ("bzip2", lambda x: bz2.decompress(x)),
                    ("deflate_auto", lambda x: zlib.decompress(x, 16 + zlib.MAX_WBITS)),
                ]
                
                for method_name, decompress_func in compression_methods:
                    try:
                        decompressed_bytes = decompress_func(compressed_content)
                        decompressed_text = decompressed_bytes.decode('utf-8')
                        json.loads(decompressed_text)  # Validate it's JSON
                        compression_method = method_name
                        decompressed_content = decompressed_text
                        break
                    except Exception:
                        continue
            
            if decompressed_content is None:
                # Try to detect if it might be a different encoding or format
                try:
                    # Try different character encodings
                    for encoding in ['utf-8', 'utf-16', 'utf-32', 'ascii', 'latin1']:
                        try:
                            decoded_text = compressed_content.decode(encoding)
                            json.loads(decoded_text)  # Validate it's JSON
                            compression_method = f"uncompressed ({encoding})"
                            decompressed_content = decoded_text
                            break
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                    
                    if decompressed_content is None:
                        return JsonResponse({
                            'status': 'error', 
                            'message': 'Failed to decompress or decode the file. Tried multiple compression methods (gzip, deflate, bzip2) and character encodings. Please check if the file is a valid compressed JSON file.'
                        })
                except Exception as e:
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Failed to process the file. Error: {str(e)}'
                    })
            
            # Parse and reformat the JSON for proper formatting
            try:
                parsed_json = json.loads(decompressed_content)
                # Format JSON with proper indentation and sorting
                formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False, sort_keys=True)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Decompressed content is not valid JSON: {str(e)}'
                })
            
            # Store the formatted JSON in session for download
            request.session['decompressed_cache_data'] = formatted_json
            original_filename = cache_file.name
            base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            request.session['decompressed_cache_filename'] = f"{base_name}_decompressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Return success without any B50 conversion
            return JsonResponse({
                'status': 'success', 
                'message': f'File successfully decompressed using {compression_method}! The decompressed JSON file is ready for download.',
                'has_decompressed_file': True,
                'compression_method': compression_method
            })
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing astro cache file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'No file uploaded or invalid request method.'})

def convert_astro_cache_to_b50(cache_data):
    """
    Convert astro cache format to B50 format.
    This function handles multiple possible cache data structures.
    """
    try:
        converted_data = {
            'old_songs': [],
            'new_songs': []
        }
        
        # Handle different possible cache data structures
        songs_list = []
        
        # Check if it's a direct list of songs
        if isinstance(cache_data, list):
            songs_list = cache_data
        # Check if it has a 'songs' key
        elif isinstance(cache_data, dict):
            # Try common keys that might contain the song data
            possible_keys = ['songs', 'data', 'entries', 'records', 'results', 'items', 'music', 'charts']
            
            # Check if it has B50-like structure first
            if 'old_songs' in cache_data and 'new_songs' in cache_data:
                return {
                    'old_songs': cache_data['old_songs'],
                    'new_songs': cache_data['new_songs']
                }
            
            # Look for song data in various possible structures
            for key in possible_keys:
                if key in cache_data:
                    potential_data = cache_data[key]
                    if isinstance(potential_data, list):
                        songs_list = potential_data
                        break
                    elif isinstance(potential_data, dict):
                        # Maybe the songs are nested deeper
                        for nested_key in possible_keys:
                            if nested_key in potential_data and isinstance(potential_data[nested_key], list):
                                songs_list = potential_data[nested_key]
                                break
                        if songs_list:
                            break
            
            # If we still haven't found song data, try to find it in the root level
            if not songs_list:
                # Look for any list that might contain song dictionaries
                for value in cache_data.values():
                    if isinstance(value, list) and value:
                        # Check if first item looks like song data
                        first_item = value[0] if isinstance(value[0], dict) else None
                        if first_item and any(key in first_item for key in ['song_name', 'title', 'name', 'music', 'chart']):
                            songs_list = value
                            break
        
        # Process each song in the list
        processed_count = 0
        for song in songs_list:
            if not isinstance(song, dict):
                continue
                
            # Try to extract song information from various possible key names
            song_name = None
            for name_key in ['song_name', 'title', 'name', 'songName', 'chart_name', 'music_name', 'track_name']:
                if name_key in song:
                    song_name = song[name_key]
                    break
            
            difficulty_type = None
            for diff_key in ['difficulty_type', 'difficulty', 'difficultyType', 'level_label', 'diff', 'chart_type']:
                if diff_key in song:
                    difficulty_type = song[diff_key]
                    break
            
            # Skip if essential data is missing
            if not song_name or not difficulty_type:
                continue
            
            # Extract other fields with fallbacks
            rank = song.get('rank') or song.get('grade') or song.get('fc') or ''
            
            achievement = None
            for ach_key in ['achievement', 'score', 'acc', 'accuracy', 'percent']:
                if ach_key in song:
                    achievement = song[ach_key]
                    break
            
            chart_difficulty = None
            for diff_key in ['chart_difficulty', 'level', 'rating', 'const', 'chart_constant']:
                if diff_key in song:
                    chart_difficulty = song[diff_key]
                    break
            
            calculated_rating = None
            for rating_key in ['calculated_rating', 'rating', 'ra', 'internal_rating']:
                if rating_key in song:
                    calculated_rating = song[rating_key]
                    break
            
            version = song.get('version') or song.get('ver') or song.get('game_version') or 'unknown'
            
            # Convert achievement to float if it's a string
            if isinstance(achievement, str):
                try:
                    achievement = float(achievement)
                except (ValueError, TypeError):
                    achievement = 0.0
            
            # Convert achievement percentage to 0-101 scale if it seems to be in 0-1 range
            if isinstance(achievement, (int, float)) and achievement <= 1.0 and achievement > 0:
                achievement = achievement * 100
            
            # Convert chart_difficulty to float if it's a string
            if isinstance(chart_difficulty, str):
                try:
                    chart_difficulty = float(chart_difficulty)
                except (ValueError, TypeError):
                    chart_difficulty = 0.0
            
            # Calculate rating if missing but we have the required data
            if not calculated_rating and chart_difficulty and achievement:
                try:
                    # Basic rating calculation (this may need adjustment based on actual formula)
                    calculated_rating = int(chart_difficulty * achievement / 100 * 22.4)
                except:
                    calculated_rating = 0

            # Detect clear type from possible locations: stats.clearType, clearType, clear_type, or clear
            raw_clear_val = None
            if isinstance(song.get('stats'), dict):
                raw_clear_val = song['stats'].get('clearType')
            raw_clear_val = raw_clear_val or song.get('clearType') or song.get('clear_type') or song.get('clear')
            try:
                raw_clear_int = int(raw_clear_val) if raw_clear_val is not None else None
            except Exception:
                raw_clear_int = None

            # Apply +1 bonus for AP/AP+ (clearType 5/6)
            try:
                rating_int = int(calculated_rating) if calculated_rating else 0
            except Exception:
                rating_int = int(calculated_rating) if calculated_rating else 0
            if raw_clear_int in (5, 6) or (isinstance(raw_clear_val, str) and raw_clear_val.strip().upper() in ('AP', 'AP+')):
                rating_int += 1

            song_data = {
                'song_name': str(song_name),
                'difficulty_type': str(difficulty_type),
                'rank': str(rank),
                'achievement': float(achievement) if achievement else 0.0,
                'chart_difficulty': float(chart_difficulty) if chart_difficulty else 0.0,
                'calculated_rating': rating_int,
                'version': str(version)
            }
            
            # Categorize as old or new song based on version information
            # PRiSM PLUS is the cutoff - everything before PRiSM PLUS is old, PRiSM PLUS+ is new
            version_lower = version.lower()
            
            # Define specific new versions (PRiSM PLUS and onwards)
            new_versions = [
                'prism plus', 'circle'
            ]
            
            # Check if it's explicitly a new version (PRiSM PLUS or later)
            is_new_version = any(new_ver in version_lower for new_ver in new_versions)
            
            if is_new_version:
                converted_data['new_songs'].append(song_data)
            else:
                # Everything else (including UNiVERSE, FESTiVAL, BUDDiES, etc.) is old
                converted_data['old_songs'].append(song_data)
            
            processed_count += 1
        
        return converted_data
        
    except Exception as e:
        # Return empty structure on conversion error
        print(f"Conversion error: {e}")  # For debugging
        return {'old_songs': [], 'new_songs': []}

def clear_b50_data(request):
    """Clear all B50 data (handled by frontend localStorage)."""
    if request.method == 'POST':
        # Since data is stored in localStorage, clearing is handled by frontend
        return JsonResponse({
            'status': 'success', 
            'message': 'B50 data cleared successfully!'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

def download_decompressed_cache(request):
    """Download the decompressed cache file stored in session."""
    if request.method == 'GET':
        try:
            decompressed_data = request.session.get('decompressed_cache_data')
            filename = request.session.get('decompressed_cache_filename', 'decompressed_cache.json')
            
            if not decompressed_data:
                return JsonResponse({'status': 'error', 'message': 'No decompressed cache data available. Please convert a cache file first.'})
            
            # Create JSON response for download
            response = HttpResponse(
                decompressed_data,
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Keep the session data so user can download again if needed
            # Session data will be cleared when a new file is processed or session expires
            
            return response
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error downloading decompressed cache: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

def convert_cache_to_b50(request):
    """Convert JSON file data to B50 format."""
    if request.method == 'POST' and request.FILES.get('json_file'):
        try:
            json_file = request.FILES['json_file']
            
            # Read and parse the JSON file
            try:
                file_content = json_file.read()
                if isinstance(file_content, bytes):
                    file_content = file_content.decode('utf-8')
                cache_data = json.loads(file_content)
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON file format.'})
            except UnicodeDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Unable to decode file. Please ensure it\'s a valid UTF-8 encoded JSON file.'})
            
            # Convert cache to B50 format
            b50_data = convert_cache_data_to_b50_format(cache_data)
            
            if b50_data['old_songs'] or b50_data['new_songs']:
                # Store the B50 data in session for download
                b50_json = json.dumps(b50_data, indent=2, ensure_ascii=False)
                request.session['converted_b50_data'] = b50_json
                original_filename = json_file.name
                base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
                request.session['converted_b50_filename'] = f"{base_name}_converted_b50_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'JSON file converted to B50 format successfully! Found {len(b50_data["old_songs"])} old songs and {len(b50_data["new_songs"])} new songs.',
                    'data': b50_data,
                    'has_b50_file': True
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'No valid song data found in JSON file. Please ensure the file contains level_metadata or similar song data structure.'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error converting JSON file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'No JSON file uploaded or invalid request method.'})

def download_converted_b50(request):
    """Download the converted B50 file stored in session."""
    if request.method == 'GET':
        try:
            b50_data = request.session.get('converted_b50_data')
            filename = request.session.get('converted_b50_filename', 'converted_b50.json')
            
            if not b50_data:
                return JsonResponse({'status': 'error', 'message': 'No converted B50 data available. Please convert a cache file first.'})
            
            # Create JSON response for download
            response = HttpResponse(
                b50_data,
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error downloading converted B50: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

def convert_cache_data_to_b50_format(cache_data):
    """Convert AstroDX cache data structure OR already converted B50 data to B50 format.
    Uses the accurate processing logic from convert_cache_data_to_all_scores_format, then selects top B50."""
    try:
        print("Converting cache data using accurate all_scores processing logic...")
        
        # Use the accurate processing from the all_scores function to get all songs first
        all_scores_data = convert_cache_data_to_all_scores_format(cache_data)
        
        # Create B50 data structure from the accurately processed all_scores
        b50_data = {
            'export_info': {
                'version': '2.0',
                'export_date': datetime.now().strftime('%Y-%m-%d'),
                'total_songs': 0,
                'note': 'Converted from AstroDX cache file using accurate processing logic'
            },
            'old_songs': [],
            'new_songs': []
        }
        
        # Get all songs from the accurate processing
        all_old_songs = all_scores_data['old_songs']
        all_new_songs = all_scores_data['new_songs']
        
        print(f"Accurate processing found: {len(all_old_songs)} old songs, {len(all_new_songs)} new songs")
        
        # NOW SELECT B50: Songs are already sorted by the all_scores function (highest first)
        # Select top 35 old + 15 new
        b50_data['old_songs'] = all_old_songs[:35]
        b50_data['new_songs'] = all_new_songs[:15]
        
        # Post-process song names to ensure proper [STD] and [DX] tags in final output
        def format_output_tags(songs_list):
            for song in songs_list:
                song_name = song['song_name']
                # Convert [ST] tags back to [STD] for output consistency
                if song_name.endswith(' [ST]'):
                    song['song_name'] = song_name[:-5] + ' [STD]'
                # [DX] tags remain as [DX] - no change needed
        
        format_output_tags(b50_data['old_songs'])
        format_output_tags(b50_data['new_songs'])
        
        b50_data['export_info']['total_songs'] = len(b50_data['old_songs']) + len(b50_data['new_songs'])
        
        print(f"B50 selection complete: {len(b50_data['old_songs'])} old songs, {len(b50_data['new_songs'])} new songs")
        
        return b50_data
        
    except Exception as e:
        print(f"Error converting cache data: {e}")
        import traceback
        traceback.print_exc()
        return {'old_songs': [], 'new_songs': [], 'export_info': {'version': '2.0', 'export_date': datetime.now().strftime('%Y-%m-%d'), 'total_songs': 0, 'note': f'Conversion failed: {str(e)}'}}

def convert_cache_to_b50_direct(request):
    """Combined function: Decompress cache file and convert directly to B50 format."""
    if request.method == 'POST' and request.FILES.get('astro_cache_file'):
        try:
            cache_file = request.FILES['astro_cache_file']
            
            # Step 1: Decompress the cache file (same logic as load_astro_cache_data)
            cache_data = None
            original_filename = cache_file.name
            
            try:
                # Read the uploaded file content
                file_content = cache_file.read()
                
                # Use the same comprehensive decompression logic as load_astro_cache_data
                cache_data = None
                decompressed_content = None
                compression_method = None
                
                # First, try to parse as uncompressed JSON
                try:
                    decompressed_text = file_content.decode('utf-8')
                    cache_data = json.loads(decompressed_text)  # Validate it's JSON
                    compression_method = "uncompressed"
                    print("Successfully loaded as uncompressed JSON")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
                
                # If not JSON, try different decompression methods
                if cache_data is None:
                    compression_methods = [
                        ("gzip", lambda x: gzip.decompress(x)),
                        ("deflate", lambda x: zlib.decompress(x)),
                        ("deflate_raw", lambda x: zlib.decompress(x, -zlib.MAX_WBITS)),
                        ("bzip2", lambda x: bz2.decompress(x)),
                        ("deflate_auto", lambda x: zlib.decompress(x, 16 + zlib.MAX_WBITS)),
                    ]
                    
                    for method_name, decompress_func in compression_methods:
                        try:
                            decompressed_bytes = decompress_func(file_content)
                            decompressed_text = decompressed_bytes.decode('utf-8')
                            cache_data = json.loads(decompressed_text)  # Validate it's JSON
                            compression_method = method_name
                            print(f"Successfully decompressed using {method_name}")
                            break
                        except Exception:
                            continue
                
                # Try different character encodings as final fallback
                if cache_data is None:
                    try:
                        for encoding in ['utf-8', 'utf-16', 'utf-32', 'ascii', 'latin1']:
                            try:
                                decoded_text = file_content.decode(encoding)
                                cache_data = json.loads(decoded_text)  # Validate it's JSON
                                compression_method = f"uncompressed ({encoding})"
                                print(f"Successfully loaded using {encoding} encoding")
                                break
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                continue
                    except Exception:
                        pass
                
                # If all methods failed
                if cache_data is None:
                    raise Exception('Failed to decompress or decode the file. Tried multiple compression methods (gzip, deflate variants, bzip2) and character encodings. Please check if the file is a valid compressed JSON file.')
            
            except Exception as decomp_error:
                return JsonResponse({'status': 'error', 'message': f'Failed to decompress or parse file: {str(decomp_error)}'})
            
            if not cache_data:
                return JsonResponse({'status': 'error', 'message': 'Failed to decompress cache file or the file is empty.'})
            
            # Step 2: Convert the decompressed cache data to B50 format
            b50_data = convert_cache_data_to_b50_format(cache_data)
            
            if b50_data['old_songs'] or b50_data['new_songs']:
                # Store the B50 data in session for download
                b50_json = json.dumps(b50_data, indent=2, ensure_ascii=False)
                request.session['converted_b50_data'] = b50_json
                base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
                request.session['converted_b50_filename'] = f"{base_name}_b50_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Cache file successfully converted to B50 format! Found {len(b50_data["old_songs"])} old songs and {len(b50_data["new_songs"])} new songs.',
                    'data': b50_data,
                    'has_b50_file': True
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'No valid song data found in cache file. Please ensure the file contains level_metadata or similar song data structure.'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing cache file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'No cache file uploaded or invalid request method.'})

@inertia('ChartDatabase')
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
        # Search both in title and aliases
        songs_qs = songs_qs.filter(
            Q(title__icontains=title) | Q(aliases__icontains=title)
        )
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
    filter_titles = list(MaimaiSong.objects.values_list('title', flat=True).distinct().order_by('title'))
    
    # Add aliases mapped to song titles for the dropdown
    alias_to_title_map = {}
    all_songs = MaimaiSong.objects.exclude(aliases__isnull=True).exclude(aliases__exact='')
    for song in all_songs:
        aliases_list = song.get_aliases_list()
        for alias in aliases_list:
            if alias.strip():  # Only add non-empty aliases
                alias_to_title_map[alias] = song.title
                # Add original title to filter list if not already there
                if song.title not in filter_titles:
                    filter_titles.append(song.title)
    
    # Sort the titles
    filter_titles = sorted(filter_titles)
    
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

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'title_kana': song.title_kana or '',
            'artist': song.artist or '',
            'catcode': song.catcode or '',
            'image_url': song.image_url or '',
            'release': song.release or '',
            'lev_bas': str(song.lev_bas) if song.lev_bas else '',
            'lev_adv': str(song.lev_adv) if song.lev_adv else '',
            'lev_exp': str(song.lev_exp) if song.lev_exp else '',
            'lev_mas': str(song.lev_mas) if song.lev_mas else '',
            'lev_remas': str(song.lev_remas) if song.lev_remas else '',
            'sort': song.sort or '',
            'version': song.version or '',
            'chart_type': song.chart_type or '',
        }
        for song in songs
    ]
    return {
        'songs': songs_data,
        'pagination': {
            'page': songs.number,
            'numPages': songs.paginator.num_pages,
            'hasPrevious': songs.has_previous(),
            'hasNext': songs.has_next(),
            'previousPage': songs.previous_page_number if songs.has_previous() else None,
            'nextPage': songs.next_page_number if songs.has_next() else None,
            'startIndex': songs.start_index(),
            'totalCount': songs.paginator.count,
        },
        'filterTitles': filter_titles,
        'filterVersions': list(filter_versions),
        'filterArtists': list(filter_artists),
        'filterCatcodes': filter_catcodes,
        'aliasToTitleMap': alias_to_title_map,
        'currentFilters': {
            'title': title,
            'version': version,
            'artist': artist,
            'catcode': catcode,
            'chartType': chart_type,
            'difficulty': difficulty,
        },
    }

def download_chart_database(request):
    """Export the entire chart database as JSON file for download."""
    try:
        # Get all songs from the database
        songs = MaimaiSong.objects.all()
        
        # Convert to list of dictionaries
        songs_data = []
        for song in songs:
            song_dict = {
                'title': song.title,
                'title_kana': song.title_kana,
                'artist': song.artist,
                'catcode': song.catcode,
                'image_url': song.image_url,
                'release': song.release,
                'lev_bas': str(song.lev_bas) if song.lev_bas else None,
                'lev_adv': str(song.lev_adv) if song.lev_adv else None,
                'lev_exp': str(song.lev_exp) if song.lev_exp else None,
                'lev_mas': str(song.lev_mas) if song.lev_mas else None,
                'lev_remas': str(song.lev_remas) if song.lev_remas else None,
                'sort': song.sort,
                'version': song.version,
                'chart_type': song.chart_type,
                'aliases': song.get_aliases_list()  # Include aliases in download
            }
            songs_data.append(song_dict)
        
        # Create the export data structure
        export_data = {
            'export_info': {
                'version': '1.0',
                'export_date': datetime.now().strftime('%Y-%m-%d'),
                'total_songs': len(songs_data),
                'note': 'Complete maimai chart database export'
            },
            'songs': songs_data
        }
        
        # Create JSON response for download
        current_date = datetime.now().strftime('%Y%m%d')
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="maimai_chart_database_{current_date}.json"'
        return response
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error exporting database: {str(e)}'})

def add_alias(request):
    """Add an alias to a song."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            song_id = data.get('song_id')
            alias = data.get('alias', '').strip()
            
            if not song_id or not alias:
                return JsonResponse({'status': 'error', 'message': 'Song ID and alias are required'})
            
            song = MaimaiSong.objects.get(id=song_id)
            aliases_list = song.get_aliases_list()
            
            # Check if alias already exists (case insensitive)
            if alias.lower() in [a.lower() for a in aliases_list]:
                return JsonResponse({'status': 'error', 'message': 'Alias already exists'})
            
            aliases_list.append(alias)
            song.set_aliases_list(aliases_list)
            song.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Alias added successfully',
                'aliases': aliases_list
            })
            
        except MaimaiSong.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Song not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error adding alias: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def remove_alias(request):
    """Remove an alias from a song."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            song_id = data.get('song_id')
            alias = data.get('alias', '').strip()
            
            if not song_id or not alias:
                return JsonResponse({'status': 'error', 'message': 'Song ID and alias are required'})
            
            song = MaimaiSong.objects.get(id=song_id)
            aliases_list = song.get_aliases_list()
            
            # Remove alias (case insensitive)
            aliases_list = [a for a in aliases_list if a.lower() != alias.lower()]
            song.set_aliases_list(aliases_list)
            song.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Alias removed successfully',
                'aliases': aliases_list
            })
            
        except MaimaiSong.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Song not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error removing alias: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def get_song_aliases(request, song_id):
    """Get aliases for a specific song."""
    try:
        song = MaimaiSong.objects.get(id=song_id)
        aliases = song.get_aliases_list()
        
        return JsonResponse({
            'status': 'success',
            'aliases': aliases,
            'song_title': song.title
        })
        
    except MaimaiSong.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error getting aliases: {str(e)}'})

@inertia('AliasUpload')
def alias_upload(request):
    """Handle alias file upload and processing."""
    if request.method == 'POST' and request.FILES.get('alias_file'):
        flash_msgs = []
        try:
            alias_file = request.FILES['alias_file']

            if alias_file.size > 5 * 1024 * 1024:
                flash_msgs.append({'type': 'danger', 'text': 'File size too large. Maximum allowed size is 5MB.'})
                request.session['alias_flash'] = flash_msgs
                return redirect('alias_upload')

            if not alias_file.name.endswith('.json'):
                flash_msgs.append({'type': 'danger', 'text': 'Invalid file type. Please upload a JSON file.'})
                request.session['alias_flash'] = flash_msgs
                return redirect('alias_upload')

            try:
                data = json.load(alias_file)
            except json.JSONDecodeError as e:
                flash_msgs.append({'type': 'danger', 'text': f'Invalid JSON format: {str(e)}'})
                request.session['alias_flash'] = flash_msgs
                return redirect('alias_upload')

            if isinstance(data, dict):
                songs_data = [data]
            elif isinstance(data, list):
                songs_data = data
            else:
                flash_msgs.append({'type': 'danger', 'text': 'JSON must be either a single object or an array of objects with "chart_name" and "chart_alias" fields.'})
                request.session['alias_flash'] = flash_msgs
                return redirect('alias_upload')

            total_processed = 0
            total_aliases_added = 0
            results = []

            for i, song_data in enumerate(songs_data):
                if not isinstance(song_data, dict):
                    results.append(f'Entry {i+1}: Invalid format - must be an object')
                    continue

                chart_name = song_data.get('chart_name')
                chart_aliases = song_data.get('chart_alias')

                if not chart_name:
                    results.append(f'Entry {i+1}: Missing "chart_name" field')
                    continue
                if not chart_aliases:
                    results.append(f'Entry {i+1}: Missing "chart_alias" field for "{chart_name}"')
                    continue
                if not isinstance(chart_aliases, list):
                    results.append(f'Entry {i+1}: "chart_alias" must be an array for "{chart_name}"')
                    continue

                song = None
                try:
                    song = MaimaiSong.objects.get(title=chart_name)
                except MaimaiSong.DoesNotExist:
                    possible_matches = MaimaiSong.objects.filter(
                        Q(title=f"{chart_name} [DX]") |
                        Q(title=f"{chart_name} [ST]") |
                        Q(title=f"{chart_name} [STD]")
                    )
                    if possible_matches.exists():
                        if possible_matches.count() == 1:
                            song = possible_matches.first()
                            results.append(f'Note: Matched "{chart_name}" to "{song.title}"')
                        else:
                            multiple_processed = 0
                            for matched_song in possible_matches:
                                existing_aliases = matched_song.get_aliases_list()
                                new_aliases_added = []
                                for alias in chart_aliases:
                                    if isinstance(alias, str) and alias.strip():
                                        clean_alias = alias.strip()
                                        if clean_alias not in existing_aliases:
                                            existing_aliases.append(clean_alias)
                                            new_aliases_added.append(clean_alias)
                                if new_aliases_added:
                                    matched_song.set_aliases_list(existing_aliases)
                                    matched_song.save()
                                    aliases_text = ', '.join([f'"{a}"' for a in new_aliases_added])
                                    results.append(f'✓ "{matched_song.title}": Added {len(new_aliases_added)} aliases ({aliases_text})')
                                    total_aliases_added += len(new_aliases_added)
                                    multiple_processed += 1
                                else:
                                    results.append(f'○ "{matched_song.title}": No new aliases added (all already exist)')
                                    multiple_processed += 1
                            total_processed += multiple_processed
                            continue
                    song = find_maimai_song_by_title(chart_name)

                if not song:
                    results.append(f'Entry {i+1}: Song "{chart_name}" not found in database')
                    continue

                existing_aliases = song.get_aliases_list()
                new_aliases_added = []
                for alias in chart_aliases:
                    if isinstance(alias, str) and alias.strip():
                        clean_alias = alias.strip()
                        if clean_alias not in existing_aliases:
                            existing_aliases.append(clean_alias)
                            new_aliases_added.append(clean_alias)

                if new_aliases_added:
                    song.set_aliases_list(existing_aliases)
                    song.save()
                    aliases_text = ', '.join([f'"{a}"' for a in new_aliases_added])
                    results.append(f'✓ "{chart_name}": Added {len(new_aliases_added)} aliases ({aliases_text})')
                    total_aliases_added += len(new_aliases_added)
                else:
                    results.append(f'○ "{chart_name}": No new aliases added (all already exist)')
                total_processed += 1

            if total_processed > 0:
                summary = f'Processed {total_processed} songs, added {total_aliases_added} new aliases total.'
                detail = '\n'.join(results)
                flash_msgs.append({'type': 'success', 'text': f'{summary}\n\nDetails:\n{detail}' if detail else summary})
            else:
                flash_msgs.append({'type': 'danger', 'text': 'No songs were processed successfully.'})
                if results:
                    flash_msgs.append({'type': 'danger', 'text': 'Errors encountered:\n' + '\n'.join(results)})

        except Exception as e:
            flash_msgs.append({'type': 'danger', 'text': f'Error processing file: {str(e)}'})

        request.session['alias_flash'] = flash_msgs
        return redirect('alias_upload')

    return {'messages': request.session.pop('alias_flash', [])}

def convert_cache_to_all_scores(request):
    """Convert cache file to show ALL played scores (not just B50)."""
    if request.method == 'POST' and request.FILES.get('cache_file'):
        try:
            cache_file = request.FILES['cache_file']
            
            # Read and decompress the cache file using same logic as existing functions
            cache_data = None
            original_filename = cache_file.name
            
            try:
                # Read the uploaded file content
                file_content = cache_file.read()
                
                # Try to parse as uncompressed JSON first
                try:
                    decompressed_text = file_content.decode('utf-8')
                    cache_data = json.loads(decompressed_text)
                    print("Successfully loaded as uncompressed JSON")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
                
                # If not JSON, try different decompression methods
                if cache_data is None:
                    compression_methods = [
                        ("gzip", lambda x: gzip.decompress(x)),
                        ("deflate", lambda x: zlib.decompress(x)),
                        ("deflate_raw", lambda x: zlib.decompress(x, -zlib.MAX_WBITS)),
                        ("bzip2", lambda x: bz2.decompress(x)),
                        ("deflate_auto", lambda x: zlib.decompress(x, 16 + zlib.MAX_WBITS)),
                    ]
                    
                    for method_name, decompress_func in compression_methods:
                        try:
                            decompressed_bytes = decompress_func(file_content)
                            decompressed_text = decompressed_bytes.decode('utf-8')
                            cache_data = json.loads(decompressed_text)
                            print(f"Successfully decompressed using {method_name}")
                            break
                        except Exception:
                            continue
                
                # Try different character encodings as final fallback
                if cache_data is None:
                    try:
                        for encoding in ['utf-8', 'utf-16', 'utf-32', 'ascii', 'latin1']:
                            try:
                                decoded_text = file_content.decode(encoding)
                                cache_data = json.loads(decoded_text)
                                print(f"Successfully loaded using {encoding} encoding")
                                break
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                continue
                    except Exception:
                        pass
                
                if cache_data is None:
                    raise Exception('Failed to decompress or decode the file.')
            
            except Exception as decomp_error:
                return JsonResponse({'status': 'error', 'message': f'Failed to decompress or parse file: {str(decomp_error)}'})
            
            if not cache_data:
                return JsonResponse({'status': 'error', 'message': 'Failed to decompress cache file or the file is empty.'})
            
            # Convert the cache data to ALL scores format (not just B50)
            all_scores_data = convert_cache_data_to_all_scores_format(cache_data)
            
            if all_scores_data['old_songs'] or all_scores_data['new_songs']:
                # Also create B35+15 selection for grid display
                b35_15_data = {
                    'old_songs': all_scores_data['old_songs'][:35],  # Top 35 old songs (already sorted)
                    'new_songs': all_scores_data['new_songs'][:15],  # Top 15 new songs (already sorted)
                }
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Cache file successfully converted! Found {len(all_scores_data["old_songs"])} old chart scores and {len(all_scores_data["new_songs"])} new chart scores.',
                    'data': all_scores_data,
                    'b35_15_data': b35_15_data  # Add B35+15 selection for grid display
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'No valid song data found in cache file.'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing cache file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'No cache file uploaded or invalid request method.'})

def convert_cache_data_to_all_scores_format(cache_data):
    """Convert cache data to ALL scores format (not limited to top 50)."""
    try:
        all_scores_data = {
            'export_info': {
                'version': '2.0',
                'export_date': datetime.now().strftime('%Y-%m-%d'),
                'total_songs': 0,
                'note': 'All played songs from cache file'
            },
            'old_songs': [],
            'new_songs': []
        }
        
        # Extract level_metadata from cache
        level_metadata = cache_data.get('level_metadata', {})
        
        if not level_metadata:
            print("No level_metadata found in cache data")
            return all_scores_data
        
        # PREPROCESSING: Better grouping using a canonical base-key and
        # explicit-vs-untagged check to assign complementary STD/DX tags.
        print("Starting tag preprocessing for paired songs (canonical grouping)...")

        def _normalize_title_for_group(s: str) -> str:
            if not s:
                return ''
            s = s.strip()
            # Basic punctuation/width normalization
            replacements = {
                '～': '~', '〜': '~', '（': '(', '）': ')', '　': ' ',
                '＃': '#', '＆': '&', '：': ':', '’': "'", '‘': "'", '“': '"', '”': '"',
                '—': '-', '–': '-', '。': '.', '、': ',', '．': '.', '･': '･'
            }
            for k, v in replacements.items():
                s = s.replace(k, v)
            s = re.sub(r'\s+', ' ', s).strip()
            # Remove trailing chart tag (DX/ST/STD) for canonical base
            s = re.sub(r'\s*\[(?:DX|ST|STD)\]\s*$', '', s, flags=re.IGNORECASE)
            return s

        canonical_map = {}
        # Build canonical groups
        for song_key, song_data in level_metadata.items():
            if not isinstance(song_data, dict):
                continue

            title = song_data.get('title', song_key)
            if not isinstance(title, str):
                title = str(title)
            title = title.replace('\r\n', '').replace('\n', '').strip()
            title = title.replace('～', '~').replace('〜', '~')
            if not title:
                continue

            canonical_base = _normalize_title_for_group(title)
            if not canonical_base:
                continue

            # Detect explicit tag presence in original title
            explicit_tag = None
            m = re.search(r'\[(DX)\]', title, re.IGNORECASE)
            if m:
                explicit_tag = 'DX'
            else:
                m2 = re.search(r'\[(ST|STD)\]', title, re.IGNORECASE)
                if m2:
                    explicit_tag = 'ST'

            entry = {
                'song_key': song_key,
                'original_title': title,
                'canonical_base': canonical_base,
                'explicit_tag': explicit_tag,
            }
            canonical_map.setdefault(canonical_base, []).append(entry)

        # For each canonical base, if there are explicit-tagged and untagged entries,
        # pair them and assign complementary tags (favor DX where indicated).
        for base, entries in canonical_map.items():
            if len(entries) < 2:
                continue

            # Separate explicit-tagged entries and untagged entries
            tagged = [e for e in entries if e['explicit_tag']]
            untagged = [e for e in entries if not e['explicit_tag']]

            if not tagged or not untagged:
                # Nothing to pair in this canonical group
                continue

            # Choose a display base from the first entry (preserve original formatting)
            display_base = re.sub(r'\s*\[(?:DX|ST|STD)\]\s*$', '', entries[0]['original_title'], flags=re.IGNORECASE).strip()

            # Pair up tagged vs untagged entries and assign titles
            # Iterate through tagged entries, match to any remaining untagged entry
            for t_entry in tagged:
                if not untagged:
                    break
                u_entry = untagged.pop(0)
                t_tag = t_entry['explicit_tag']

                if t_tag == 'DX':
                    # Keep tagged entry as DX, mark the untagged as STD
                    new_untagged_title = f"{display_base} [STD]"
                    level_metadata[u_entry['song_key']]['title'] = new_untagged_title
                    print(f"Tag assignment (cache check): '{u_entry['original_title']}' → '{new_untagged_title}'")
                else:
                    # If tagged is ST/STD, normalize to [STD] and mark the other as [DX]
                    new_tagged_title = f"{display_base} [STD]"
                    new_untagged_title = f"{display_base} [DX]"
                    level_metadata[t_entry['song_key']]['title'] = new_tagged_title
                    level_metadata[u_entry['song_key']]['title'] = new_untagged_title
                    print(f"Tag assignment (cache check): '{t_entry['original_title']}' → '{new_tagged_title}'")
                    print(f"Tag assignment (cache check): '{u_entry['original_title']}' → '{new_untagged_title}'")

        print("Tag preprocessing completed.")
        
        for song_key, song_data in level_metadata.items():
            if not isinstance(song_data, dict):
                continue
                
            # Use the title from song_data, fallback to song_key
            song_name = song_data.get('title', song_key).strip()
            
            # Clean up song name (remove extra whitespace/newlines)
            clean_song_name = song_name.replace('\r\n', '').replace('\n', '').strip()
            if not clean_song_name:
                continue
            
            # Get difficulties array
            difficulties_array = song_data.get('difficulties', [])
            if not isinstance(difficulties_array, list):
                continue
            
            # Process each difficulty in the array
            for difficulty_obj in difficulties_array:
                if not isinstance(difficulty_obj, dict):
                    continue
                
                # Extract difficulty info
                difficulty_alias = difficulty_obj.get('alias', '')
                stats = difficulty_obj.get('stats', {})
                
                if not isinstance(stats, dict):
                    continue
                
                # Extract achievement rate from stats
                achievement_rate = stats.get('achievementRate', 0)
                
                # Skip songs without play data (achievementRate = 0)
                if achievement_rate == 0:
                    continue

                # Skip Easy difficulties explicitly — database uses Basic/STD, not 'Easy'
                if isinstance(difficulty_alias, str) and difficulty_alias.lower() in ['easy', 'e']:
                    print(f"Skipping Easy difficulty for {clean_song_name} (alias: {difficulty_alias})")
                    continue
                
                # Use the assigned title (possibly modified by tag preprocessing) as first lookup
                # If the cache title starts with a front tag like '[宴]' or '[宴/バディ/2P]', skip it
                # per user request: do not attempt name searching on front-tagged entries.
                if re.match(r'^\[[^\]]+\]\s*', clean_song_name):
                    print(f"Skipping front-tagged song (cache): {clean_song_name}")
                    continue

                assigned_title = clean_song_name
                # Ensure base_name is available for candidate generation and fallback logic
                base_name = clean_song_name
                # Prefer the robust lookup helper which handles tag variants and aliases
                song_db = find_maimai_song_by_title(assigned_title)

                if not song_db:
                    # Normalize title for lookup: strip trailing chart tag and normalize [ST] -> [STD]
                    base_name = clean_song_name
                    # Normalize common trailing tags
                    if clean_song_name.endswith(' [DX]'):
                        base_name = clean_song_name[:-5].strip()
                    elif clean_song_name.endswith(' [ST]'):
                        # Treat [ST] as [STD] in the DB
                        base_name = clean_song_name[:-5].strip()
                    elif clean_song_name.endswith(' [STD]'):
                        base_name = clean_song_name[:-6].strip()

                    # Prefer candidates that match the requested chart tag (DX/STD) if present
                    requested_tag = None
                    if re.search(r'\[\s*DX\s*\]$', clean_song_name, re.IGNORECASE):
                        requested_tag = 'DX'
                    elif re.search(r'\[\s*ST\s*\]$', clean_song_name, re.IGNORECASE) or re.search(r'\[\s*STD\s*\]$', clean_song_name, re.IGNORECASE):
                        requested_tag = 'STD'

                    if requested_tag == 'DX':
                        tags = ['DX', 'STD', 'ST']
                    elif requested_tag == 'STD':
                        tags = ['STD', 'ST', 'DX']
                    else:
                        tags = ['STD', 'ST', 'DX']

                    candidates = []
                    for t in tags:
                        candidates.append(f"{base_name} [{t}]")
                        candidates.append(f"{base_name}[{t}]")
                    candidates.append(base_name)

                    # Helper to normalize alias/title for comparison
                    def normalize_key(s):
                        if not s:
                            return ''
                        s2 = s.strip()
                        # remove trailing tag if present
                        for t in [' [DX]', '[DX]', ' [ST]', '[ST]', ' [STD]', '[STD]']:
                            if s2.endswith(t):
                                s2 = s2[:-len(t)].strip()
                        return s2.lower()

                    # Try exact title match for each candidate (exact first)
                    for candidate in candidates:
                        try:
                            song_db = MaimaiSong.objects.get(title=candidate)
                            break
                        except MaimaiSong.DoesNotExist:
                            continue

                    # If still not found, try case-insensitive exact match on candidates
                    if not song_db:
                        for candidate in candidates:
                            song_db = MaimaiSong.objects.filter(title__iexact=candidate).first()
                            if song_db:
                                break

                    # If still not found, try checking aliases (case-insensitive) using normalized base name
                    if not song_db:
                        songs_with_aliases = MaimaiSong.objects.filter(aliases__isnull=False)
                        base_norm = normalize_key(base_name)
                        for s in songs_with_aliases:
                            aliases_list = s.get_aliases_list()
                            for alias in aliases_list:
                                if normalize_key(alias) == base_norm:
                                    song_db = s
                                    break
                            if song_db:
                                break

                    # Final fallback: partial match in title using base_name
                    if not song_db:
                        song_db = MaimaiSong.objects.filter(title__icontains=base_name).first()
                
                # Skip if we can't find the song in database
                if not song_db:
                    print(f"Song not found in database: {base_name}")
                    continue
                
                # Before mapping, if the matched DB record lacks the requested difficulty,
                # try to find an alternative DB entry for the same base name that has it.
                # Map difficulty alias to database field name
                difficulty_type_mapped = difficulty_alias
                alias_l = difficulty_alias.lower()
                field_name = None
                if alias_l in ['basic', 'bas', 'bsc']:
                    field_name = 'lev_bas'
                    difficulty_type_mapped = 'Basic'
                elif alias_l in ['advanced', 'adv']:
                    field_name = 'lev_adv'
                    difficulty_type_mapped = 'Advanced'
                elif alias_l in ['expert', 'exp']:
                    field_name = 'lev_exp'
                    difficulty_type_mapped = 'Expert'
                elif alias_l in ['master', 'mas']:
                    field_name = 'lev_mas'
                    difficulty_type_mapped = 'Master'
                elif alias_l in ['remaster', 'remas', 're:master']:
                    field_name = 'lev_remas'
                    difficulty_type_mapped = 'Re:Master'

                # If we have a field to check and the current DB match lacks it, search alternatives
                if song_db and field_name:
                    try:
                        current_val = getattr(song_db, field_name, None)
                    except Exception:
                        current_val = None

                    if not current_val:
                        # Candidate title variants - prefer requested tag order when possible
                        requested_tag = None
                        if re.search(r'\[\s*DX\s*\]$', assigned_title, re.IGNORECASE):
                            requested_tag = 'DX'
                        elif re.search(r'\[\s*ST\s*\]$', assigned_title, re.IGNORECASE) or re.search(r'\[\s*STD\s*\]$', assigned_title, re.IGNORECASE):
                            requested_tag = 'STD'

                        if requested_tag == 'DX':
                            tags = ['DX', 'STD', 'ST']
                        elif requested_tag == 'STD':
                            tags = ['STD', 'ST', 'DX']
                        else:
                            tags = ['STD', 'ST', 'DX']

                        candidates = []
                        for t in tags:
                            candidates.append(f"{base_name} [{t}]")
                            candidates.append(f"{base_name}[{t}]")
                        candidates.append(base_name)

                        # Local normalize helper
                        def normalize_key_local(s):
                            if not s:
                                return ''
                            s2 = s.strip()
                            for t in [' [DX]', '[DX]', ' [ST]', '[ST]', ' [STD]', '[STD]']:
                                if s2.endswith(t):
                                    s2 = s2[:-len(t)].strip()
                            return s2.lower()

                        found_alt = None
                        # Exact title matches
                        for cand in candidates:
                            try:
                                alt = MaimaiSong.objects.get(title=cand)
                                if getattr(alt, field_name, None):
                                    found_alt = alt
                                    break
                            except MaimaiSong.DoesNotExist:
                                continue

                        # Case-insensitive exact match
                        if not found_alt:
                            for cand in candidates:
                                alt = MaimaiSong.objects.filter(title__iexact=cand).first()
                                if alt and getattr(alt, field_name, None):
                                    found_alt = alt
                                    break

                        # Alias-based search
                        if not found_alt:
                            songs_with_aliases = MaimaiSong.objects.filter(aliases__isnull=False)
                            base_norm = normalize_key_local(base_name)
                            for s in songs_with_aliases:
                                try:
                                    aliases_list = s.get_aliases_list()
                                except Exception:
                                    aliases_list = []
                                for alias in aliases_list:
                                    if normalize_key_local(alias) == base_norm:
                                        if getattr(s, field_name, None):
                                            found_alt = s
                                            break
                                if found_alt:
                                    break

                        if found_alt:
                            song_db = found_alt
                            print(f"Switched DB match for {base_name} - {difficulty_alias} to {song_db.title} (has {field_name})")

                # Map difficulty alias to database field and get chart difficulty
                chart_difficulty = None
                
                if difficulty_alias.lower() in ['basic', 'bas', 'bsc']:
                    chart_difficulty = song_db.lev_bas
                    difficulty_type_mapped = 'Basic'
                elif difficulty_alias.lower() in ['advanced', 'adv']:
                    chart_difficulty = song_db.lev_adv
                    difficulty_type_mapped = 'Advanced'
                elif difficulty_alias.lower() in ['expert', 'exp']:
                    chart_difficulty = song_db.lev_exp
                    difficulty_type_mapped = 'Expert'
                elif difficulty_alias.lower() in ['master', 'mas']:
                    chart_difficulty = song_db.lev_mas
                    difficulty_type_mapped = 'Master'
                elif difficulty_alias.lower() in ['remaster', 'remas', 're:master']:
                    chart_difficulty = song_db.lev_remas
                    difficulty_type_mapped = 'Re:Master'
                
                # Skip if we don't have chart difficulty
                if not chart_difficulty:
                    # Detailed debug: show what DB record we matched and what level fields it has
                    try:
                        db_info = {
                            'matched_title': getattr(song_db, 'title', None),
                            'lev_bas': getattr(song_db, 'lev_bas', None),
                            'lev_adv': getattr(song_db, 'lev_adv', None),
                            'lev_exp': getattr(song_db, 'lev_exp', None),
                            'lev_mas': getattr(song_db, 'lev_mas', None),
                            'lev_remas': getattr(song_db, 'lev_remas', None),
                            'chart_type': getattr(song_db, 'chart_type', None),
                        }
                        print(f"Chart difficulty not found for {base_name} - {difficulty_alias}. DB match: {db_info}")
                    except Exception as _e:
                        print(f"Chart difficulty not found for {base_name} - {difficulty_alias}. (Could not inspect DB record) Error: {_e}")
                    continue
                
                chart_difficulty = float(chart_difficulty)
                
                # Calculate rank based on achievement using the same system as the main calculator
                rank = ""
                achievement_decimal = Decimal(str(achievement_rate))
                if Decimal('60') <= achievement_decimal < Decimal('70'):
                    rank = 'B'
                elif Decimal('70') <= achievement_decimal < Decimal('75'):
                    rank = '2B'
                elif Decimal('75') <= achievement_decimal < Decimal('80'):
                    rank = '3B'
                elif Decimal('80') <= achievement_decimal < Decimal('90'):
                    rank = 'A'
                elif Decimal('90') <= achievement_decimal < Decimal('94'):
                    rank = '2A'
                elif Decimal('94') <= achievement_decimal < Decimal('97'):
                    rank = '3A'
                elif Decimal('97') <= achievement_decimal < Decimal('98'):
                    rank = 'S'
                elif Decimal('98') <= achievement_decimal < Decimal('99'):
                    rank = 'S+'
                elif Decimal('99') <= achievement_decimal < Decimal('99.5'):
                    rank = '2S'
                elif Decimal('99.5') <= achievement_decimal < Decimal('100'):
                    rank = '2S+'
                elif Decimal('100') <= achievement_decimal < Decimal('100.5'):
                    rank = '3S'
                elif achievement_decimal >= Decimal('100.5'):
                    rank = '3S+'
                else:
                    rank = 'B'

                # Use the same coefficient table as the main calculator
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
                
                # Cap achievement at 100.5 for calculation only
                achievement_for_calc = achievement_decimal
                if achievement_for_calc > Decimal('100.5'):
                    achievement_for_calc = Decimal('100.5')
                
                # Calculate rating using the same method as main calculator
                chart_difficulty_decimal = Decimal(str(chart_difficulty))
                calculated_rating = (chart_difficulty_decimal * coefficient * achievement_for_calc / 100).to_integral_value(rounding=ROUND_DOWN)
                
                # Get version from database (fallback to 'Unknown' if not set)
                version = song_db.version or 'Unknown'
                
                # Prefer the assigned title (may include tag assigned earlier); override with DB title if it contains explicit tag
                final_song_name = assigned_title
                if song_db.title and (' [DX]' in song_db.title or ' [STD]' in song_db.title):
                    final_song_name = song_db.title
                else:
                    # Check if the found song has a chart_type field we can use
                    if hasattr(song_db, 'chart_type') and song_db.chart_type:
                        if song_db.chart_type.upper() == 'DX':
                            final_song_name = f"{base_name} [DX]"
                        elif song_db.chart_type.upper() in ['STD', 'ST']:
                            final_song_name = f"{base_name} [STD]"
                
                # Create song entry
                # Map clearType to human-readable clear label (FC, FC+, AP, AP+)
                clear_label = None
                raw_clear = stats.get('clearType')
                try:
                    raw_clear_int = int(raw_clear) if raw_clear is not None else None
                except Exception:
                    raw_clear_int = None

                if raw_clear_int == 3:
                    clear_label = 'FC'
                elif raw_clear_int == 4:
                    clear_label = 'FC+'
                elif raw_clear_int == 5:
                    clear_label = 'AP'
                elif raw_clear_int == 6:
                    clear_label = 'AP+'

                # Apply +1 bonus to calculated rating for AP/AP+ clear types (clearType 5 or 6)
                try:
                    rating_int = int(calculated_rating)
                except Exception:
                    rating_int = int(calculated_rating) if calculated_rating else 0

                if raw_clear_int in (5, 6):
                    rating_int += 1

                song_entry = {
                    'song_name': final_song_name,
                    'difficulty_type': difficulty_type_mapped,
                    'rank': rank,
                    'achievement': float(achievement_rate),
                    'chart_difficulty': float(chart_difficulty),
                    'calculated_rating': rating_int,
                    'version': version,
                    'clear_type': clear_label
                }
                
                # Categorize as old or new song based on version
                version_lower = version.lower()
                
                # Define specific new versions (PRiSM PLUS and onwards)
                new_versions = [
                    'prism plus', 'circle'
                ]
                
                # Check if it's explicitly a new version (PRiSM PLUS or later)
                is_new_version = any(new_ver in version_lower for new_ver in new_versions)
                
                if is_new_version:
                    all_scores_data['new_songs'].append(song_entry)
                else:
                    # Everything else (including UNiVERSE, FESTiVAL, BUDDiES, etc.) is old
                    all_scores_data['old_songs'].append(song_entry)
        
        # Sort by rating (highest first), then by achievement for ties
        # NOTE: Unlike B50 conversion, we do NOT limit the results here - we keep ALL scores
        all_scores_data['old_songs'].sort(key=lambda x: (x['calculated_rating'], x['achievement']), reverse=True)
        all_scores_data['new_songs'].sort(key=lambda x: (x['calculated_rating'], x['achievement']), reverse=True)
        
        # Remove duplicate entries (same song + difficulty) keeping only the highest score
        def deduplicate_songs(songs_list):
            """Keep only the highest score for each unique song+difficulty combination."""
            seen = {}
            deduplicated = []
            
            for song in songs_list:
                key = (song['song_name'], song['difficulty_type'])
                if key not in seen or song['calculated_rating'] > seen[key]['calculated_rating'] or \
                   (song['calculated_rating'] == seen[key]['calculated_rating'] and song['achievement'] > seen[key]['achievement']):
                    seen[key] = song
                    
            # Convert back to list, sorted by rating
            return sorted(seen.values(), key=lambda x: (x['calculated_rating'], x['achievement']), reverse=True)
        
        # Apply deduplication to both old and new songs
        all_scores_data['old_songs'] = deduplicate_songs(all_scores_data['old_songs'])
        all_scores_data['new_songs'] = deduplicate_songs(all_scores_data['new_songs'])
        
        all_scores_data['export_info']['total_songs'] = len(all_scores_data['old_songs']) + len(all_scores_data['new_songs'])
        
        print(f"Converted cache data to ALL scores: {len(all_scores_data['old_songs'])} old songs, {len(all_scores_data['new_songs'])} new songs (after deduplication)")
        
        return all_scores_data
        
    except Exception as e:
        print(f"Error converting cache data: {e}")
        import traceback
        traceback.print_exc()
        return {'old_songs': [], 'new_songs': [], 'export_info': {'version': '2.0', 'export_date': datetime.now().strftime('%Y-%m-%d'), 'total_songs': 0, 'note': f'Conversion failed: {str(e)}'}}
