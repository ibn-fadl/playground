package com.apap.demo.controller;

/**
 * @author ...
 * created by putu.edy in 2025
 */

import com.apap.demo.model.Music;
import com.apap.demo.service.MusicService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
public class MusicController {

    @Autowired
    MusicService musicService;

    @RequestMapping(value = "", method = RequestMethod.GET)
    public ResponseEntity getAllMusic() {
        //TODO
        return null;
    }

    @RequestMapping(value = "", method = RequestMethod.POST)
    public ResponseEntity addMusic(@RequestBody Music music) {
        //TODO
        return null;
    }

    @RequestMapping(value = "", method = RequestMethod.DELETE)
    public ResponseEntity deleteMusic(@PathVariable String kodeLagu) {
        //TODO
       return null;
    }

    @RequestMapping(value = "", method = RequestMethod.PUT)
    public ResponseEntity updateMusic(@RequestBody Music music) {
        //TODO
        return null;
    }

}
