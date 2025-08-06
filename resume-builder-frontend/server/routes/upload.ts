import { RequestHandler } from "express";
import multer from "multer";

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 5 * 1024 * 1024, // 5MB limit
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'));
    }
  }
});

export const handleUpload: RequestHandler = async (req, res) => {
  try {
    // Use multer middleware
    upload.single('file')(req, res, async (err) => {
      if (err) {
        console.error('Multer error:', err);
        return res.status(400).json({ 
          error: err.message === 'Only PDF files are allowed' 
            ? 'Only PDF files are supported' 
            : 'File upload failed'
        });
      }

      if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
      }

      const { target_role, user_input } = req.body;

      if (!target_role) {
        return res.status(400).json({ error: 'Target role is required' });
      }

      try {
        // Create FormData for the backend API
        const FormData = (await import('form-data')).default;
        const formData = new FormData();
        
        formData.append('file', req.file.buffer, {
          filename: req.file.originalname,
          contentType: req.file.mimetype,
        });
        formData.append('target_role', target_role);
        formData.append('user_input', user_input || '');

        // Forward to FastAPI backend
        const backendUrl = process.env.BACKEND_URL || 'http://localhost:7777';
        const response = await fetch(`${backendUrl}/api/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          let errorMessage = `Backend error: ${response.status}`;
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.error || errorMessage;
          } catch {
            errorMessage = response.statusText || errorMessage;
          }
          throw new Error(errorMessage);
        }

        // Check content type of response
        const contentType = response.headers.get('content-type');
        
        if (contentType?.includes('application/pdf')) {
          // Forward PDF response
          const pdfBuffer = await response.arrayBuffer();
          
          res.setHeader('Content-Type', 'application/pdf');
          res.setHeader('Content-Disposition', `attachment; filename="resume_${req.file.originalname}"`);
          res.send(Buffer.from(pdfBuffer));
        } else {
          // Forward JSON response
          const data = await response.json();
          res.json(data);
        }
      } catch (error) {
        console.error('Backend request error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Failed to process resume'
        });
      }
    });
  } catch (error) {
    console.error('Upload route error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};
