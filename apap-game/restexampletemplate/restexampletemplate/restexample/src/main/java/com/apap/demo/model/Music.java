package com.apap.demo.model;

/**
 * @author 
 * created by putu.edy in 2025
 */
public class Music {

    private String kodeLagu;   // unique ID for the song
    private String judulLagu;  // title of the song
    private String penyanyi;   // artist/singer
    private String genre;      // genre of the music
    

    public Music(String kodeLagu, String judulLagu, String penyanyi, String genre) {
        this.kodeLagu = kodeLagu;
        this.judulLagu = judulLagu;
        this.penyanyi = penyanyi;
        this.genre = genre;
    }

    public String getKodeLagu() {
        return kodeLagu;
    }

    public void setKodeLagu(String kodeLagu) {
        this.kodeLagu = kodeLagu;
    }

    public String getJudulLagu() {
        return judulLagu;
    }

    public void setJudulLagu(String judulLagu) {
        this.judulLagu = judulLagu;
    }

    public String getPenyanyi() {
        return penyanyi;
    }

    public void setPenyanyi(String penyanyi) {
        this.penyanyi = penyanyi;
    }

    public String getGenre() {
        return genre;
    }

    public void setGenre(String genre) {
        this.genre = genre;
    }
}
 
