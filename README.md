# GenAI-Course

cd /Users/sundaranbu/Desktop/Sundar_genai_course/GenAI-Course
git add Rag/data/document.txt
git commit -m "Add more documentation content"
git push origin feat-sundar


gcloud compute ssh ragbot-vm --zone=asia-south1-a
cd ~/GenAI-Course
git pull
cd Rag
source .venv/bin/activate
python3 build_index.py
sudo systemctl restart ragbot