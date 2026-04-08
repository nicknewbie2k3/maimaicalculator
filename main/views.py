import json
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from datetime import datetime
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib import messages
from .models import OldSong, NewSong, MaimaiSong

def parse_decimal(val):
    try:
        return Decimal(val)
    except (InvalidOperation, TypeError, ValueError):
        return None

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

            # Return song data as JSON for localStorage handling
            song_data = {
                'song_name': song_name,
                'difficulty_type': difficulty_type,
                'rank': rank,
                'achievement': float(achievement),
                'chart_difficulty': float(chart_difficulty),
                'calculated_rating': int(calculated_rating),
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
    
    return render(request, "main/calculator_list.html", {
        "old_songs": [],
        "new_songs": [],
        "merged_grid": [[None] * 5 for _ in range(10)],  # Empty 10x5 grid
        "total_rating": 0,
        "old_total_rating": 0,
        "new_total_rating": 0,
        "total_average_rating": 0,
        "all_song_names": all_song_names,
        "maimai_songs_dict": maimai_songs_dict,
        "alias_to_title_map": alias_to_title_map,
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
                
                # Handle aliases separately (whether created or updated)
                aliases = entry.get('aliases', [])
                if aliases:
                    obj.set_aliases_list(aliases)
                    obj.save()
            # Remove songs not in the uploaded file
            MaimaiSong.objects.exclude(title__in=uploaded_titles).delete()
            message = f"Upload successful. {len(uploaded_titles)} songs now in the database."
        except Exception as e:
            message = f"Error processing file: {e}"
    return render(request, "main/databaseUpload.html", {"message": message})

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
                            maimai_song = MaimaiSong.objects.filter(title=song.get('song_name', '')).first()
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
            
            # Return the data for frontend localStorage handling
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

def clear_b50_data(request):
    """Clear all B50 data (handled by frontend localStorage)."""
    if request.method == 'POST':
        # Since data is stored in localStorage, clearing is handled by frontend
        return JsonResponse({
            'status': 'success', 
            'message': 'B50 data cleared successfully!'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

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

    return render(request, "main/chart_database.html", {
        "songs": songs,
        "filter_titles": filter_titles,
        "filter_versions": filter_versions,
        "filter_artists": filter_artists,
        "filter_catcodes": filter_catcodes,
        "alias_to_title_map": alias_to_title_map,
    })

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

def alias_upload(request):
    """Handle alias file upload and processing."""
    if request.method == 'POST' and request.FILES.get('alias_file'):
        try:
            alias_file = request.FILES['alias_file']
            
            # Check file size (5MB limit)
            if alias_file.size > 5 * 1024 * 1024:
                messages.error(request, 'File size too large. Maximum allowed size is 5MB.')
                return render(request, "main/alias_upload.html")
            
            # Check file extension
            if not alias_file.name.endswith('.json'):
                messages.error(request, 'Invalid file type. Please upload a JSON file.')
                return render(request, "main/alias_upload.html")
            
            # Parse JSON data
            try:
                data = json.load(alias_file)
            except json.JSONDecodeError as e:
                messages.error(request, f'Invalid JSON format: {str(e)}')
                return render(request, "main/alias_upload.html")
            
            # Handle both single song object and array of songs
            songs_data = []
            if isinstance(data, dict):
                # Single song format
                songs_data = [data]
            elif isinstance(data, list):
                # Multiple songs format
                songs_data = data
            else:
                messages.error(request, 'JSON must be either a single object or an array of objects with "chart_name" and "chart_alias" fields.')
                return render(request, "main/alias_upload.html")
            
            # Process each song
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
                
                # Find the song in database with flexible matching
                song = None
                
                # First try exact match
                try:
                    song = MaimaiSong.objects.get(title=chart_name)
                except MaimaiSong.DoesNotExist:
                    # Try matching with [DX] and [STD] tags
                    possible_matches = MaimaiSong.objects.filter(
                        Q(title=f"{chart_name} [DX]") | 
                        Q(title=f"{chart_name} [STD]")
                    )
                    
                    if possible_matches.exists():
                        if possible_matches.count() == 1:
                            # Only one match found
                            song = possible_matches.first()
                            results.append(f'Note: Matched "{chart_name}" to "{song.title}"')
                        else:
                            # Multiple matches - process all
                            multiple_processed = 0
                            for matched_song in possible_matches:
                                # Get existing aliases
                                existing_aliases = matched_song.get_aliases_list()
                                
                                # Add new aliases (avoid duplicates)
                                new_aliases_added = []
                                for alias in chart_aliases:
                                    if isinstance(alias, str) and alias.strip():
                                        clean_alias = alias.strip()
                                        if clean_alias not in existing_aliases:
                                            existing_aliases.append(clean_alias)
                                            new_aliases_added.append(clean_alias)
                                
                                if new_aliases_added:
                                    # Update the song with new aliases
                                    matched_song.set_aliases_list(existing_aliases)
                                    matched_song.save()
                                    
                                    aliases_text = ', '.join([f'"{alias}"' for alias in new_aliases_added])
                                    results.append(f'✓ "{matched_song.title}": Added {len(new_aliases_added)} aliases ({aliases_text})')
                                    total_aliases_added += len(new_aliases_added)
                                    multiple_processed += 1
                                else:
                                    results.append(f'○ "{matched_song.title}": No new aliases added (all already exist)')
                                    multiple_processed += 1
                            
                            total_processed += multiple_processed
                            continue  # Skip the single song processing below
                
                if not song:
                    results.append(f'Entry {i+1}: Song "{chart_name}" not found in database (tried exact match and [DX]/[STD] variants)')
                    continue
                
                # Get existing aliases
                existing_aliases = song.get_aliases_list()
                
                # Add new aliases (avoid duplicates)
                new_aliases_added = []
                for alias in chart_aliases:
                    if isinstance(alias, str) and alias.strip():
                        clean_alias = alias.strip()
                        if clean_alias not in existing_aliases:
                            existing_aliases.append(clean_alias)
                            new_aliases_added.append(clean_alias)
                
                if new_aliases_added:
                    # Update the song with new aliases
                    song.set_aliases_list(existing_aliases)
                    song.save()
                    
                    aliases_text = ', '.join([f'"{alias}"' for alias in new_aliases_added])
                    results.append(f'✓ "{chart_name}": Added {len(new_aliases_added)} aliases ({aliases_text})')
                    total_aliases_added += len(new_aliases_added)
                else:
                    results.append(f'○ "{chart_name}": No new aliases added (all already exist)')
                
                total_processed += 1
            
            # Show summary results
            if total_processed > 0:
                summary = f'Processed {total_processed} songs, added {total_aliases_added} new aliases total.'
                if results:
                    detail_message = '\n'.join(results)
                    messages.success(request, f'{summary}\n\nDetails:\n{detail_message}')
                else:
                    messages.success(request, summary)
            else:
                messages.error(request, 'No songs were processed successfully.')
                if results:
                    error_details = '\n'.join(results)
                    messages.error(request, f'Errors encountered:\n{error_details}')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            
        return render(request, "main/alias_upload.html")
    
    # GET request - just show the page
    return render(request, "main/alias_upload.html")
