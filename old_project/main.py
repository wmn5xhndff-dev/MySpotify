import old_project.logic as logic
import old_project.print_menu as print_menu
def main():
    songs = logic.load()
    while True:
        print_menu.print_menu()
        choice = input()
        if choice == "1":
            logic.show_songs(songs)
            input("Нажмите Enter что бы вернутся")
        elif choice == "2":
            print_menu.print_confirm()
            x = input()
            if x == "1":
                while True:
                    logic.add(songs)
                    again = input("1. Добавить еще \nEnter. Если хотите выйти ")
                    if again == "1":
                        continue
                    elif again == "":
                        break
            elif x == "2":
                continue
        elif choice == "3":
            query = input("\nКакую песню или артиста найти:\n")
            logic.search(songs,query)
        elif choice == "4":
            logic.show_songs(songs)
            raw_index = (input("\nНапишите номер песни которую хотите удалить: "))
            if raw_index == "":
                continue
            if not raw_index.isdigit():
                print("Ошибка ведите число")
                continue
            else: index = int(raw_index)
            
            print_menu.print_confirm()
            x = input()
            if x == "1":
                logic.delete(songs, index)
            elif x == "2":
                continue
        elif choice == "5":
            logic.show_songs(songs)
            index = (input("\nНомер песни (или enter для отмены): "))
            if index == "":
                continue
            if not index.isdigit():
                print("Ошибка: Введите число!")
                continue
            index = int(index)
            if index > len(songs):
                print("Песни с таким номером нет!")
                continue
            print_menu.print_confirm()
            x = input()
            if x == "1":
                logic.redact(songs, index)
            elif x == "2":
                continue
        elif choice == "6":
            print("Сортировка:")
            print("1. По артисту: \n2. По названию: \n3. По дате добавления (сначала новые): ")
            n = input()
            if n not in ['1','2','3']:
                print("Ошибка выберите 1, 2 или 3")
                continue
            logic.sort(songs, n)
        elif choice == "7":
            print("До свидание!")
            break
        else:
            print("Не правильная задача")

main()