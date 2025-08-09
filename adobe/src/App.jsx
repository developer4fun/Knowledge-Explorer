import React,
{
    useState,
    useEffect
}
from 'react';
import FileUpload from './components/FileUpload';
import PDFViewer from './components/PDFViewer';
import RelatedSectionsSidebar from './components/RelatedSectionsSidebar';
import InsightsBulb from './components/InsightsBulb';
import PodcastPlayer from './components/PodcastPlayer';

// --- Web Worker for processing ---
const processingWorker = new Worker(new URL('./workers/processing.js',
    import.meta.url));

function App() {
    const [pdfFile, setPdfFile] = useState(null);
    const [docData, setDocData] = useState(null);
    const [currentSection, setCurrentSection] = useState(null);
    const [recommendations, setRecommendations] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // --- Handle messages from the web worker ---
        processingWorker.onmessage = (e) => {
            const {
                type,
                payload
            } = e.data;
            if (type === 'recommendations') {
                setRecommendations(payload);
                setIsLoading(false);
            }
        };
    }, []);

    const handleFileSelect = async (file) => {
        setIsLoading(true);
        setError(null);
        setPdfFile(file);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:5001/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('File upload failed');
            }

            const data = await response.json();
            setDocData(data);

            // --- Store data in IndexedDB via worker ---
            processingWorker.postMessage({
                type: 'init_db',
                payload: {
                    docId: data.filename,
                    sections: data.sections
                }
            });

        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSectionChange = (sectionIndex) => {
        if (docData && docData.sections[sectionIndex]) {
            setCurrentSection({ ...docData.sections[sectionIndex],
                index: sectionIndex
            });
            // --- Get recommendations from the backend (or worker) ---
            fetchRecommendations(docData.filename, sectionIndex);
        }
    };

    const fetchRecommendations = async (docId, sectionIndex) => {
        setIsLoading(true);
        // --- Using backend for recommendations ---
        try {
            const response = await fetch('http://localhost:5001/recommendations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doc_id: docId,
                    current_section_index: sectionIndex
                }),
            });
            const recs = await response.json();
            setRecommendations(recs);
        } catch (err) {
            console.error("Failed to fetch recommendations from backend:", err);
        } finally {
            setIsLoading(false);
        }

        // --- Example of using worker for offline recommendations ---
        // processingWorker.postMessage({
        //     type: 'get_recommendations',
        //     payload: { docId: docId, currentSectionIndex: sectionIndex }
        // });
    };


    return (
        <div className="flex h-screen font-sans bg-gray-100">
      <div className="w-1/4 bg-white border-r border-gray-200 p-4 overflow-y-auto">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">PDF Explorer</h1>
        <FileUpload onFileSelect={handleFileSelect} isLoading={isLoading} />
        {error && <p className="text-red-500 mt-2">{error}</p>}
        {docData && (
          <RelatedSectionsSidebar
            sections={docData.sections}
            recommendations={recommendations}
            onSectionSelect={handleSectionChange}
            isLoading={isLoading}
          />
        )}
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex-grow relative">
          {pdfFile ? (
            <PDFViewer fileUrl={URL.createObjectURL(pdfFile)} onSectionChange={handleSectionChange} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Upload a PDF to get started</p>
            </div>
          )}
          {currentSection && <InsightsBulb section={currentSection} />}
        </div>
        {currentSection && <PodcastPlayer section={currentSection} />}
      </div>
    </div>
    );
}

export default App;