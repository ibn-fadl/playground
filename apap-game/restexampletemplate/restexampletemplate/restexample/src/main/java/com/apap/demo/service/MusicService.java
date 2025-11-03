package com.apap.demo.service;

/**
 * @author 
 * created by putu.edy in 2025
 */

import com.apap.demo.model.Music;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class MusicService {

    List<Music> musicList = new ArrayList<>();

    public MusicService() {
        Music music1 = new Music("M01", "Bohemian Rhapsody", "Queen", "Rock");
        Music music2 = new Music("M02", "Garam dan Madu (sakit dadaku)", "Tenxi, Naykilla & Jemsii ", "Dangdut hiphop");
        Music music3 = new Music("M03", "Swweetest Scar", "Prince Husein", "Pop");
        Music music4 = new Music("M04", "Psychosocial", "Slipknot", "Metal");
        Music music5 = new Music("M04", "Maling", "Sukses lancar rejeki", "Punk");


        musicList.add(music1);
        musicList.add(music2);
        musicList.add(music3);
        musicList.add(music4);
        musicList.add(music5);
    }

    public List<Music> getAllMusic() {
        //TODO
        return null;
    }

    public void add(Music music) {
        //TODO
    }

    public void delete(String kodeLagu) {
        //TODO
    }

    public void update(Music music) {
        //TODO
    }
}
