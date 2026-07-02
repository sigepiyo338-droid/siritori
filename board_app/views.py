from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Post
from .forms import PostForm

def board_list(request):
    posts = Post.objects.all()
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            new_post = form.save(commit=False)
            if request.user.is_authenticated:
                new_post.user = request.user
            new_post.save()
            messages.success(request, '投稿しました。')
            return redirect('board:board_list')
    else:
        form = PostForm()
    
    return render(request, 'board/board_list.html', {
        'posts': posts,
        'form': form,
    })

@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    # ログインユーザーが自分の投稿のみ削除可能
    if post.user == request.user:
        if request.method == 'POST':
            post.delete()
            messages.success(request, '投稿を削除しました。')
            return redirect('board:board_list')
    else:
        messages.error(request, '他人の投稿は削除できません。')
        return redirect('board:board_list')

