let db;

const initDB = (docId, sections) => {
    const request = indexedDB.open("pdfDocs", 1);

    request.onupgradeneeded = (event) => {
        db = event.target.result;
        if (!db.objectStoreNames.contains('documents')) {
            db.createObjectStore('documents', {
                keyPath: 'id'
            });
        }
    };

    request.onsuccess = (event) => {
        db = event.target.result;
        storeDocument(docId, sections);
    };

    request.onerror = (event) => {
        console.error("IndexedDB error:", event.target.errorCode);
    };
};

const storeDocument = (docId, sections) => {
    if (!db) return;
    const transaction = db.transaction(['documents'], 'readwrite');
    const store = transaction.objectStore('documents');
    // Here you would also store the pre-computed TF-IDF vectors
    store.put({
        id: docId,
        sections: sections
    });
};


self.onmessage = (e) => {
    const {
        type,
        payload
    } = e.data;

    if (type === 'init_db') {
        initDB(payload.docId, payload.sections);
    } else if (type === 'get_recommendations') {
        // In a real implementation, you would get data from IndexedDB
        // and perform TF-IDF calculations here.
        console.log("Worker received request for recommendations:", payload);

        // Mock response
        const mockRecommendations = [{
            section_title: "Offline Recommendation 1",
            page_number: 1
        }, {
            section_title: "Offline Recommendation 2",
            page_number: 5
        }, ];

        self.postMessage({
            type: 'recommendations',
            payload: mockRecommendations
        });
    }
};