import torch
import os
import argparse
from tqdm import tqdm
from PIL import Image
import numpy as np
from transformers import AutoProcessor
from torchvision.transforms import Compose, CenterCrop, ToTensor, ToPILImage
import os
import torch
from transformers import AutoModelForCausalLM, AutoProcessor
import argparse
import cv2
import torch
import numpy as np
import random
import torch
import json
import os
from tqdm import tqdm
import torch
from transformers import AutoModel, AutoTokenizer
import torch
from PIL import Image
from decord import VideoReader, cpu
import torch
import numpy as np
import matplotlib.pyplot as plt
import os
import cv2
import torch
import transformers
import gc
from videoxlpro.videoxlpro.demo_utils import process_video, load_image_processor, generate_response
from transformers import AutoTokenizer, AutoModelForCausalLM
import warnings

# 禁用一些警告
transformers.logging.set_verbosity_error()
warnings.filterwarnings('ignore')

seed = 42
torch.manual_seed(seed)
np.random.seed(seed)
random.seed(seed)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False



def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cached-data-root', type=str, default='./data/dvf_recons', help='the data root for frames in the reconstruction structure')
    parser.add_argument('--output-dir', type=str, default='./outputs/mm_representations', help='the output directory')
    parser.add_argument('--output-fn', type=str, default='loki.json', help='the output file name')
    return parser.parse_args()


def get_dataset_meta(dataset_path):
    fns = sorted(os.listdir(dataset_path))
    meta = {}
    for fn in fns:
        data_id = fn.rsplit('_', maxsplit=1)[0]
        if data_id not in meta:
            meta[data_id] = 1
        else:
            meta[data_id] += 1
    return meta



def get_dataset_mp4(dataset_path):
    # 获取目录下所有文件，并过滤出 .mp4 文件
    mp4_files = sorted([fn for fn in os.listdir(dataset_path) if fn.endswith('.mp4')])
    
    # 返回绝对路径
    return [os.path.join(dataset_path, fn) for fn in mp4_files]

def sample_by_interval(frame_count, interval=200):
    sampled_index = []
    count = 1
    while count <= frame_count:
        sampled_index.append(count)
        count += interval
    return sampled_index



    # 设置设备
device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 模型路径
model_path = "/home/ubuntu/202502/Video-XL-Pro-3B"
    # video_path = "/path/to/your/video.mp4"

    # 使用 Auto 类加载模型
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    low_cpu_mem_usage=True, 
    torch_dtype=torch.float16,
    attn_implementation="flash_attention_2",
    device_map=device,
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    trust_remote_code=True
)

image_processor = load_image_processor(model, tokenizer)









@torch.inference_mode()
def infer(video_path):

    
    # question1 = "You have been shown one video, which might be taken from real world or generated by an advanced AI model. \nIs this video taken in the real world? (Answer yes if you think it is taken in the real world, and answer no otherwise.)\n."
    

    max_frames_num = 64

    # 处理视频
    video_tensor = process_video(video_path, image_processor, model.device, max_frames_num)

    # 生成参数
    gen_kwargs = {
        "do_sample": True,
        "temperature": 0.01,
        "top_p": 0.001,
        "num_beams": 1,
        "use_cache": True,
        "max_new_tokens": 256
    }

    # 文本提示
    prompt = "You have been shown one video, which might be taken from real world or generated by an advanced AI model. \nIs this video taken in the real world? (Answer yes if you think it is taken in the real world, and answer no otherwise.)\n."

    text = f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n<image>\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    response = generate_response(model, tokenizer, text, video_tensor, gen_kwargs)

    # 4. 输出结果
    print("\n===== 生成的回答 =====")
    print(response)

    # question2 = "Now, analyze whether this video is AI-generated or recorded in the real world from multiple perspectives. Consider: (1) visual details (textures, imperfections, fine details), (2) realism (natural lighting, reflections, shadows), (3) motion (fluidity, natural physics, consistency), and (4) any inconsistencies that might suggest AI generation (e.g., unnatural blurring, strange artifacts, facial distortions)."
    
    # # question2 = "Then, analyze from different perspectives whether this video is AI-generated or recorded in the real world. Overly smooth camera movement in AI-generated video, with unnatural fluidity and an absence of typical human imperfections or natural pauses."
    # # question2 = "Tell me if there are synthetic artifacts in the video or not?"
    
    # output2, chat_history = model.chat(video_path=video_path, tokenizer=tokenizer, user_prompt=question2, chat_history=chat_history, return_history=True, max_num_frames=max_num_frames, generation_config=generation_config)
    # print("文本输出2:",output2)
    
    # question3 = "Finally, based on your analysis, this video might be taken from real world or generated by an advanced AI model. Is this video taken in the real world? (Answer yes if you think it is taken in the real world, and answer no otherwise.)"
    # output3, chat_history = model.chat(video_path=video_path, tokenizer=tokenizer, user_prompt=question3, chat_history=chat_history, return_history=True, max_num_frames=max_num_frames, generation_config=generation_config)
    # print("文本输出3:",output3)


    first_three_chars = response.strip()[:3].lower()  # 获取前三个字符并转换为小写
    bool_value = first_three_chars == "yes"  # 如果是"yes"，则设置为True

    print("is_ai_generated:",bool_value)  # True 或 False

    # return selected_layer_final,pooled_mm_feature
    return response,bool_value


if __name__ == '__main__':
    config = parse_args().__dict__
    output_dir = config['output_dir']
    output_fn = config['output_fn']  # This should be your JSON output filename
    input_data_root = config['cached_data_root']
    cls_folder = sorted(os.listdir(input_data_root))
    cls_folder = list(filter(lambda x: os.path.isdir(os.path.join(input_data_root, x)), cls_folder))
    print(f'Find {len(cls_folder)} classes: {cls_folder}')
    
    # Initialize a list to store all JSON entries
    json_output = []
    
    with torch.inference_mode():
        for cls_idx, sub_cls in enumerate(cls_folder, 1):
            # Directly process files in the class directory, skipping the label level
            os.makedirs(os.path.join(output_dir, sub_cls), exist_ok=True)
            
            dataset_mp4 = get_dataset_mp4(os.path.join(input_data_root, sub_cls))
            
            for data_id in tqdm(dataset_mp4):
                try:
                    file_name = os.path.basename(data_id)
                    file, _ = os.path.splitext(file_name)
                    
                    # Perform inference
                    output1,bool_value = infer(data_id)
                    question2 = "You have been shown one video, which might be taken from real world or generated by an advanced AI model. \nIs this video taken in the real world? (Answer yes if you think it is taken in the real world, and answer no otherwise.)\n."
    
                    # Create JSON entry similar to your example
                    entry = {
                        "id": file,  # Using filename as ID
                        "conversations": [
                            {
                                "from": "human",
                                "value": "<image>\n" + question2  # Your question text
                            },
                            {
                                "from": "gpt",
                                "value": output1   # Your answer text
                            }
                        ],
                        "data_source": sub_cls,  # Now just using sub_cls without label
                        "video_path": data_id,  # Full video path or relative path
                        "answer": output1
                    }
                    
                    # Add to JSON output list
                    json_output.append(entry)
                    
                    # Save tensor data if needed
                    output_path = os.path.join(output_dir, sub_cls, f"{file}.pth")
                    if not (os.path.exists(output_path) and os.path.getsize(output_path) > 0):
                        result_dict = {
                            "text1": output1,
                            "bool_value": bool_value,
                        }
                        torch.save(result_dict, output_path)
                
                except Exception as e:
                    print(f"Error processing video {data_id}: {e}")
        
            print(f'Finished {cls_idx}/{len(cls_folder)}')
    
        # Save the JSON output
        with open(os.path.join(output_dir, output_fn), 'w') as f:
            json.dump(json_output, f, indent=2)
        print(f"JSON output saved to {os.path.join(output_dir, output_fn)}")