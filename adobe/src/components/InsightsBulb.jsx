import React, { useState } from 'react';

function InsightsBulb({ section }) {
  const [insights, setInsights] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const fetchInsights = async () => {
    if (!section) return;
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: section.content }),
      });
      const data = await response.json();
      setInsights(data);
    } catch (error) {
      console.error('Failed to fetch insights:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBulbClick = () => {
    setIsOpen(!isOpen);
    if (!insights) {
      fetchInsights();
    }
  };

  return (
    <>
      <button
        onClick={handleBulbClick}
        className="absolute bottom-4 right-4 bg-yellow-400 hover:bg-yellow-500 text-white font-bold rounded-full h-12 w-12 flex items-center justify-center shadow-lg"
        title="Get Insights"
      >
        💡
      </button>

      {isOpen && (
        <div className="absolute bottom-20 right-4 w-80 bg-white rounded-lg shadow-xl p-4 border border-gray-200">
          <h3 className="font-bold text-lg mb-2">Insights for "{section.title}"</h3>
          {isLoading ? (
            <p>Loading insights...</p>
          ) : insights ? (
            <div>
              <h4 className="font-semibold mt-2">Key Points:</h4>
              <ul className="list-disc list-inside text-sm">
                {insights.key_points.map((point, index) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
              <h4 className="font-semibold mt-2">Did you know?</h4>
              <p className="text-sm">{insights.did_you_know}</p>
            </div>
          ) : (
            <p>No insights available.</p>
          )}
        </div>
      )}
    </>
  );
}

export default InsightsBulb;