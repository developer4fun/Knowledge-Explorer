import React, { useState, useRef } from 'react';

function PodcastPlayer({ section }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const audioRef = useRef(null);

  const handlePlayPause = async () => {
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      if (audioRef.current && audioRef.current.src) {
        audioRef.current.play();
        setIsPlaying(true);
      } else {
        setIsLoading(true);
        try {
          const response = await fetch('http://localhost:5001/podcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: `Summary for ${section.title}. ${section.content.substring(0, 200)}` }),
          });
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          audioRef.current.src = url;
          audioRef.current.play();
          setIsPlaying(true);
        } catch (error) {
          console.error('Failed to generate podcast:', error);
        } finally {
          setIsLoading(false);
        }
      }
    }
  };
  
  return (
    <div className="bg-gray-800 text-white p-4 flex items-center justify-between">
      <div className="font-semibold">Podcast Mode: "{section.title}"</div>
      <button
        onClick={handlePlayPause}
        className="bg-violet-500 hover:bg-violet-600 text-white font-bold py-2 px-4 rounded-full"
        disabled={isLoading}
      >
        {isLoading ? 'Generating...' : isPlaying ? 'Pause' : 'Play'}
      </button>
      <audio ref={audioRef} onEnded={() => setIsPlaying(false)} />
    </div>
  );
}

export default PodcastPlayer;