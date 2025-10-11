from django.db import models





class OldSong(models.Model):
    song_name = models.CharField(max_length=100)
    rank = models.CharField(max_length=8)  # Changed to CharField for rank options
    achievement = models.DecimalField(max_digits=7, decimal_places=4)
    chart_difficulty = models.DecimalField(max_digits=3, decimal_places=1)
    calculated_rating = models.IntegerField(default=0)
    difficulty_type = models.CharField(max_length=16, default="")  # Added field

    def __str__(self):
        return f"OldSong(song_name={self.song_name}, rank={self.rank}, achievement={self.achievement}, chart_difficulty={self.chart_difficulty}, calculated_rating={self.calculated_rating}, difficulty_type={self.difficulty_type})"




class NewSong(models.Model):
    song_name = models.CharField(max_length=100)
    rank = models.CharField(max_length=8)  # Changed to CharField for rank options
    achievement = models.DecimalField(max_digits=7, decimal_places=4)
    chart_difficulty = models.DecimalField(max_digits=3, decimal_places=1)
    calculated_rating = models.IntegerField(default=0)
    difficulty_type = models.CharField(max_length=16, default="")  # Added field

    def __str__(self):
        return f"NewSong(song_name={self.song_name}, rank={self.rank}, achievement={self.achievement}, chart_difficulty={self.chart_difficulty}, calculated_rating={self.calculated_rating}, difficulty_type={self.difficulty_type})"




class MaimaiSong(models.Model):
    title = models.CharField(max_length=200)
    title_kana = models.CharField(max_length=200, blank=True, null=True)
    artist = models.CharField(max_length=200, blank=True, null=True)
    catcode = models.CharField(max_length=100, blank=True, null=True)
    image_url = models.URLField(max_length=300, blank=True, null=True)
    release = models.CharField(max_length=20, blank=True, null=True)
    lev_bas = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    lev_adv = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    lev_exp = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    lev_mas = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    lev_remas = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    sort = models.CharField(max_length=20, blank=True, null=True)
    version = models.CharField(max_length=100, blank=True, null=True)
    chart_type = models.CharField(max_length=10, blank=True, null=True)  # Added for [STD]/[DX] distinction

    def __str__(self):
        return f"{self.title} ({self.version}, {self.chart_type})"