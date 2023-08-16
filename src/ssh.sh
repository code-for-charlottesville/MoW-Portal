function get_name(){
  name=$(docker ps)
  arr=($name)
  for i in "${!arr[@]}";
  do
    if [[ ${arr[$i+1]} == "src_web" ]]; then
      echo "${arr[$i]}"
    fi
    #echo $i
    #echo "${arr[$i]}"
    # do whatever on $i
  done
}

docker exec -it `get_name` bash
