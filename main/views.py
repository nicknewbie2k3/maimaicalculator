import json
import zlib
import gzip
import bz2
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
            
            song_data = {
                'song_name': str(song_name),
                'difficulty_type': str(difficulty_type),
                'rank': str(rank),
                'achievement': float(achievement) if achievement else 0.0,
                'chart_difficulty': float(chart_difficulty) if chart_difficulty else 0.0,
                'calculated_rating': int(calculated_rating) if calculated_rating else 0,
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
                    # Try matching with [DX] and [ST] tags
                    possible_matches = MaimaiSong.objects.filter(
                        Q(title=f"{chart_name} [DX]") | 
                        Q(title=f"{chart_name} [ST]")
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
                    results.append(f'Entry {i+1}: Song "{chart_name}" not found in database (tried exact match and [DX]/[ST] variants)')
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
        
        # PREPROCESSING: Group songs by base name and assign complementary tags
        print("Starting tag preprocessing for paired songs...")
        song_groups = {}
        
        # Step 1: Group songs by base name
        for song_key, song_data in level_metadata.items():
            if not isinstance(song_data, dict):
                continue
                
            title = song_data.get('title', song_key).strip()
            title = title.replace('\r\n', '').replace('\n', '').strip()
            
            if not title:
                continue
            
            # Extract base name and chart tag
            base_name = title
            chart_tag = None
            
            if title.endswith(' [DX]'):
                base_name = title[:-5]  # Remove ' [DX]'
                chart_tag = 'DX'
            elif title.endswith(' [ST]'):
                base_name = title[:-5]  # Remove ' [ST]'
                chart_tag = 'ST'
            elif title.endswith(' [STD]'):
                base_name = title[:-6]  # Remove ' [STD]'
                chart_tag = 'ST'  # Treat STD as ST for processing
            
            if base_name not in song_groups:
                song_groups[base_name] = []
            
            song_groups[base_name].append({
                'song_key': song_key,
                'original_title': title,
                'base_name': base_name,
                'chart_tag': chart_tag
            })
        
        # Step 2: Process groups with exactly 2 songs for tag assignment
        for base_name, songs in song_groups.items():
            if len(songs) == 2:
                song1, song2 = songs
                
                # Case 1: One has tag, one doesn't - assign complementary tag
                if song1['chart_tag'] and not song2['chart_tag']:
                    complementary_tag = 'DX' if song1['chart_tag'] == 'ST' else 'ST'
                    new_title = f"{base_name} [{complementary_tag}]"
                    level_metadata[song2['song_key']]['title'] = new_title
                    print(f"Tag assignment: '{song2['original_title']}' → '{new_title}'")
                    
                elif song2['chart_tag'] and not song1['chart_tag']:
                    complementary_tag = 'DX' if song2['chart_tag'] == 'ST' else 'ST'
                    new_title = f"{base_name} [{complementary_tag}]"
                    level_metadata[song1['song_key']]['title'] = new_title
                    print(f"Tag assignment: '{song1['original_title']}' → '{new_title}'")
                
                # Case 2: Neither has tag - no action (let database lookup handle it)
                # Case 3: Both have tags - no action (already properly tagged)
        
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
                
                # Search for song in database using the same method as the main project
                song_db = None
                
                # First try exact match
                try:
                    song_db = MaimaiSong.objects.get(title=clean_song_name)
                except MaimaiSong.DoesNotExist:
                    # Try matching with [DX] and [STD] tags
                    possible_matches = MaimaiSong.objects.filter(
                        Q(title=f"{clean_song_name} [DX]") | 
                        Q(title=f"{clean_song_name} [STD]")
                    )
                    
                    if possible_matches.exists():
                        song_db = possible_matches.first()
                
                # If still not found, try case-insensitive exact match
                if not song_db:
                    song_db = MaimaiSong.objects.filter(title__iexact=clean_song_name).first()
                
                # If still not found, try checking aliases
                if not song_db:
                    # Search in songs that have aliases containing this song name
                    songs_with_aliases = MaimaiSong.objects.filter(aliases__isnull=False)
                    for song in songs_with_aliases:
                        aliases_list = song.get_aliases_list()
                        if any(clean_song_name.lower() == alias.lower() for alias in aliases_list):
                            song_db = song
                            break
                
                # Final fallback: partial match in title
                if not song_db:
                    song_db = MaimaiSong.objects.filter(title__icontains=clean_song_name).first()
                
                # Skip if we can't find the song in database
                if not song_db:
                    print(f"Song not found in database: {clean_song_name}")
                    continue
                
                # Map difficulty alias to database field and get chart difficulty
                chart_difficulty = None
                difficulty_type_mapped = difficulty_alias
                
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
                    print(f"Chart difficulty not found for {clean_song_name} - {difficulty_alias}")
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
                
                # Use the clean song name or database title
                final_song_name = clean_song_name
                if song_db.title and (' [DX]' in song_db.title or ' [STD]' in song_db.title):
                    final_song_name = song_db.title
                else:
                    # Check if the found song has a chart_type field we can use
                    if hasattr(song_db, 'chart_type') and song_db.chart_type:
                        if song_db.chart_type.upper() == 'DX':
                            final_song_name = f"{clean_song_name} [DX]"
                        elif song_db.chart_type.upper() in ['STD', 'ST']:
                            final_song_name = f"{clean_song_name} [STD]"
                
                # Create song entry
                song_entry = {
                    'song_name': final_song_name,
                    'difficulty_type': difficulty_type_mapped,
                    'rank': rank,
                    'achievement': float(achievement_rate),
                    'chart_difficulty': float(chart_difficulty),
                    'calculated_rating': int(calculated_rating),
                    'version': version
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
